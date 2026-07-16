#!/usr/bin/env python3
"""
git-guard — PreToolUse hook (matcher: Bash).

Personal, user-level safety net enforcing:
  1. Never commit (incl. --amend), merge, `reset --hard`, or force-push while
     HEAD is on a protected branch (main/master).
  2. Never create a feature branch (git switch -c / checkout -b / branch
     <new>) in the PRIMARY worktree — steer to `git worktree add` instead.
  3. Every newly created branch (via switch/checkout/branch/worktree add)
     must follow the conventionalbranch.org naming shape
     <type>/<kebab-description>, with a permissive type superset (see
     BRANCH_TYPES) and uppercase tolerated for ticket IDs.
  4. Each repo is evaluated independently, against its own live state, read
     at execution time via `git rev-parse` (not string pattern-matching).

This is a hard-deny gate: every violation blocks. The only bypass is the
GIT_GUARD_OFF=1 environment variable, checked first.

Design notes:
  - Commands may arrive prefixed by RTK (`git status` -> `rtk git status`);
    both the raw and RTK-rewritten forms are normalized before matching.
  - Commands may be chained (&&, ||, ;, |); subcommands are walked in order,
    tracking `cd` and `git -C` so a chain like
    `git switch feat && git commit` is judged against the branch feat lands
    on, not the stale live HEAD.
  - Fails OPEN on anything it can't confidently parse or resolve (not a repo,
    detached HEAD, unparsable quoting, subprocess failure) — it only ever
    blocks positively-identified git operations against a positively-resolved
    protected branch / primary worktree. It never touches non-git Bash.

Exit codes:
  0 - allow (default; also used whenever the command isn't a recognized,
      positively-blocked git operation)
  2 - deny; human-readable reason printed to stderr and surfaced to the model
"""

from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROTECTED = {"main", "master"}

BRANCH_NON_CREATE_FLAGS = {
    "-d", "-D", "-m", "-M", "-c", "-C", "-a", "-l", "-r", "-v", "-vv",
    "--list", "--show-current", "--all", "--delete", "--move", "--copy",
    "--remotes",
}

READONLY_TOKENS = {"--help", "-h", "--version"}

# ---------------------------------------------------------------------------
# Branch naming convention (conventionalbranch.org), permissive superset.
# ---------------------------------------------------------------------------

# Superset of the strict spec (feature/bugfix/hotfix/release/chore): also
# accepts `fix` (used by ico-ai-tooling's GitHub convention) and `docs`.
BRANCH_TYPES = {"feature", "bugfix", "hotfix", "release", "chore", "fix", "docs"}

# Base/long-lived branches are exempt from naming (they're never "created"
# in the sense this convention governs).
BRANCH_NAME_EXEMPT = {"main", "master", "develop"}

# Shape: <type>/<segment>(-<segment>)* ; segments are alnum (+ '.' for
# release versions like 1.2.3); uppercase allowed to accommodate ticket IDs
# (e.g. feature/CLIN-12345-desc) — a deliberate deviation from the strict
# spec's all-lowercase rule. No leading/trailing/consecutive hyphens.
_BRANCH_NAME_RE = re.compile(
    r"^(?:" + "|".join(sorted(BRANCH_TYPES)) + r")/"
    r"[A-Za-z0-9](?:[A-Za-z0-9.]|-(?=[A-Za-z0-9.]))*$"
)


def is_valid_branch_name(name: str) -> bool:
    if name in BRANCH_NAME_EXEMPT:
        return True
    return bool(_BRANCH_NAME_RE.match(name))


def naming_reason(name: str) -> str:
    types = ", ".join(sorted(BRANCH_TYPES))
    return (
        f"Blocked: branch name '{name}' doesn't follow the conventional "
        f"branch format <type>/<kebab-description> (types: {types}). "
        f"Example: feature/CLIN-12345-add-widget. "
        f"See ~/.claude/rules/git-worktree-harness.md. "
        f"Bypass: GIT_GUARD_OFF=1."
    )


# ---------------------------------------------------------------------------
# git helpers — fail open (return None) on any error
# ---------------------------------------------------------------------------

def _run_git(directory: str, args: list[str]) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", directory] + args,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired, ValueError):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def get_branch(directory: str) -> str | None:
    return _run_git(directory, ["rev-parse", "--abbrev-ref", "HEAD"])


def is_primary_worktree(directory: str) -> bool:
    git_dir = _run_git(directory, ["rev-parse", "--git-dir"])
    common_dir = _run_git(directory, ["rev-parse", "--git-common-dir"])
    if not git_dir or not common_dir:
        return False  # fail open: can't confirm, don't block

    def _abs(p: str) -> str:
        if not os.path.isabs(p):
            p = os.path.join(directory, p)
        return os.path.realpath(p)

    return _abs(git_dir) == _abs(common_dir)


def resolve_path(base: str, path: str) -> str:
    path = os.path.expanduser(path)
    if os.path.isabs(path):
        return os.path.normpath(path)
    return os.path.normpath(os.path.join(base, path))


# ---------------------------------------------------------------------------
# Command splitting — best-effort, quote-aware, fails open on parse errors
# ---------------------------------------------------------------------------

def split_subcommands(command: str) -> list[str]:
    subs: list[str] = []
    current: list[str] = []
    quote: str | None = None
    i = 0
    n = len(command)
    while i < n:
        c = command[i]
        if quote:
            current.append(c)
            if c == quote and command[i - 1] != "\\":
                quote = None
            i += 1
            continue
        if c in ("'", '"'):
            quote = c
            current.append(c)
            i += 1
            continue
        if command[i:i + 2] in ("&&", "||"):
            subs.append("".join(current))
            current = []
            i += 2
            continue
        if c in (";", "|"):
            subs.append("".join(current))
            current = []
            i += 1
            continue
        current.append(c)
        i += 1
    subs.append("".join(current))
    return [s.strip() for s in subs if s.strip()]


def strip_rtk_prefix(command: str) -> str:
    command = re.sub(r"(?<![\w-])rtk\s+proxy\s+", "", command)
    command = re.sub(r"(?<![\w-])rtk\s+", "", command)
    return command


# ---------------------------------------------------------------------------
# git subcommand parsing helpers
# ---------------------------------------------------------------------------

def parse_switch_checkout(args: list[str]) -> tuple[bool, str | None]:
    """args excludes the leading 'switch'/'checkout' token."""
    create = False
    target = None
    positional: list[str] = []
    i = 0
    while i < len(args):
        a = args[i]
        if a in ("-c", "-C", "-b", "-B"):
            create = True
            if i + 1 < len(args):
                target = args[i + 1]
                i += 2
                continue
        elif not a.startswith("-"):
            positional.append(a)
        i += 1
    if target is None and positional:
        target = positional[0]
    return create, target


def parse_branch_create(args: list[str]) -> tuple[bool, str | None]:
    """args excludes the leading 'branch' token."""
    if any(a in BRANCH_NON_CREATE_FLAGS for a in args):
        return False, None
    positional = [a for a in args if not a.startswith("-")]
    if not positional:
        return False, None
    return True, positional[0]


def parse_worktree(args: list[str]) -> tuple[bool, str | None]:
    """args excludes the leading 'worktree' token.

    Only `worktree add ... -b/-B <name>` creates a new branch; `add` of an
    existing branch (no -b/-B) or any other worktree subcommand (list,
    remove, prune, ...) does not.
    """
    if not args or args[0] != "add":
        return False, None
    rest = args[1:]
    i = 0
    while i < len(rest):
        a = rest[i]
        if a in ("-b", "-B"):
            if i + 1 < len(rest):
                return True, rest[i + 1]
            return False, None
        i += 1
    return False, None


def parse_push_target(args: list[str], current_branch: str | None) -> tuple[bool, str | None]:
    """args excludes the leading 'push' token. Returns (is_force, target_branch)."""
    is_force = any(
        a == "-f" or a == "--force" or a.startswith("--force-with-lease")
        for a in args
    )
    positional = [a for a in args if not a.startswith("-")]
    refspec = positional[1] if len(positional) >= 2 else None
    if refspec:
        target = refspec.split(":", 1)[1] if ":" in refspec else refspec
    else:
        target = current_branch
    return is_force, (target or None)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def deny(reason: str) -> None:
    print(f"[git-guard] {reason}", file=sys.stderr)
    sys.exit(2)


def main() -> None:
    if os.environ.get("GIT_GUARD_OFF"):
        sys.exit(0)

    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError, ValueError):
        sys.exit(0)

    if data.get("tool_name") != "Bash":
        sys.exit(0)

    command = (data.get("tool_input") or {}).get("command", "")
    if not command or not isinstance(command, str):
        sys.exit(0)

    command = strip_rtk_prefix(command)
    subcommands = split_subcommands(command)

    state = {
        "dir": data.get("cwd") or os.getcwd(),
        "sim_branch": None,  # set once a switch/checkout lands in this chain
    }

    def current_branch() -> str | None:
        if state["sim_branch"] is not None:
            return state["sim_branch"]
        return get_branch(state["dir"])

    for sub in subcommands:
        try:
            tokens = shlex.split(sub)
        except ValueError:
            continue  # unbalanced quotes etc. — fail open
        if not tokens:
            continue

        if any(t in READONLY_TOKENS for t in tokens):
            continue  # probe command — never gated

        if tokens[0] == "cd":
            target = tokens[1] if len(tokens) > 1 else "~"
            if target != "-":  # can't resolve `cd -`; fail open, keep old dir
                state["dir"] = resolve_path(state["dir"], target)
                state["sim_branch"] = None
            continue

        if tokens[0] != "git":
            continue

        rest = tokens[1:]
        sub_dir = state["dir"]
        overridden = False
        if rest[:1] == ["-C"] and len(rest) >= 2:
            sub_dir = resolve_path(state["dir"], rest[1])
            rest = rest[2:]
            overridden = True

        if not rest:
            continue
        op, args = rest[0], rest[1:]

        if op == "commit":
            branch = current_branch() if not overridden else get_branch(sub_dir)
            if branch in PROTECTED:
                deny(
                    f"Blocked: direct commit to protected branch '{branch}' in "
                    f"{sub_dir}. Create a feature branch in a worktree instead "
                    f"(git worktree add ../<name> -b <branch>). "
                    f"Bypass: GIT_GUARD_OFF=1."
                )

        elif op == "merge":
            branch = current_branch() if not overridden else get_branch(sub_dir)
            if branch in PROTECTED:
                deny(
                    f"Blocked: local merge into protected branch '{branch}' in "
                    f"{sub_dir}. Use the PR flow instead of merging locally on "
                    f"{branch}. Bypass: GIT_GUARD_OFF=1."
                )

        elif op == "reset":
            if "--hard" in args:
                branch = current_branch() if not overridden else get_branch(sub_dir)
                if branch in PROTECTED:
                    deny(
                        f"Blocked: 'git reset --hard' on protected branch "
                        f"'{branch}' in {sub_dir}. Bypass: GIT_GUARD_OFF=1."
                    )

        elif op == "push":
            branch = current_branch() if not overridden else get_branch(sub_dir)
            is_force, target = parse_push_target(args, branch)
            if is_force and target in PROTECTED:
                deny(
                    f"Blocked: force-push to protected branch '{target}' from "
                    f"{sub_dir}. Bypass: GIT_GUARD_OFF=1."
                )

        elif op in ("switch", "checkout"):
            create, target = parse_switch_checkout(args)
            if create and is_primary_worktree(sub_dir):
                deny(
                    f"Blocked: branch creation in the primary worktree "
                    f"({sub_dir}). Feature branches must be created in a "
                    f"linked worktree: git worktree add ../<name> -b <branch>. "
                    f"Bypass: GIT_GUARD_OFF=1."
                )
            if create and target and not is_valid_branch_name(target):
                deny(naming_reason(target))
            if target and not overridden:
                state["sim_branch"] = target

        elif op == "branch":
            create, target = parse_branch_create(args)
            if create and is_primary_worktree(sub_dir):
                deny(
                    f"Blocked: branch creation in the primary worktree "
                    f"({sub_dir}). Feature branches must be created in a "
                    f"linked worktree: git worktree add ../<name> -b <branch>. "
                    f"Bypass: GIT_GUARD_OFF=1."
                )
            if create and target and not is_valid_branch_name(target):
                deny(naming_reason(target))

        elif op == "worktree":
            creates, target = parse_worktree(args)
            # Sanctioned path — no primary-worktree location check here,
            # only naming.
            if creates and target and not is_valid_branch_name(target):
                deny(naming_reason(target))

    sys.exit(0)


if __name__ == "__main__":
    main()
