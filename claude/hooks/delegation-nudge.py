#!/usr/bin/env python3
"""
Delegation nudge — UserPromptSubmit hook.

Detects prompts that look decomposable into independent subtasks and injects
a short reminder to fan them out to parallel subagents per
~/.claude/rules/delegation.md (a user-level file, not project-relative),
instead of doing everything inline on the orchestrator's own model.

This is a soft nudge, not a gate: no hook can force decomposition, so this
only makes the right behavior salient at decision time. It stays silent on
short / single-step / read-only prompts to avoid banner fatigue.

Exit code is always 0 — this hook informs, it never blocks.
"""

import hashlib
import json
import os
import re
import sys
import tempfile
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ---------------------------------------------------------------------------
# Parse stdin
# ---------------------------------------------------------------------------

try:
    _raw = sys.stdin.read()
    data = json.loads(_raw)
except (json.JSONDecodeError, EOFError, ValueError):
    sys.exit(0)

# ---------------------------------------------------------------------------
# Detection
# ---------------------------------------------------------------------------

IMPERATIVE_VERBS = (
    "analyze|analyse|audit|review|investigate|research|check|look into|"
    "explore|examine|inspect|refactor|implement|build|create|write|fix|"
    "update|migrate|test|deploy|design|plan|compare|summarize|summarise|"
    "document|generate|configure|set up|setup|wire|integrate|validate|"
    "verify|scaffold|debug|prepare"
)

# Splits a prompt on hard clause boundaries (newline, semicolon) and on
# coordinating conjunctions that are immediately followed by another
# imperative verb — this avoids splitting ordinary noun-phrase "and"s like
# "cats and dogs".
_CLAUSE_SPLIT_RE = re.compile(
    r"[\n;]+"
    r"|\band\s+then\b"
    r"|\bthen\b"
    r"|\balso\b"
    r"|\bas\s+well\s+as\b"
    r"|,?\s+and\s+(?=(?:" + IMPERATIVE_VERBS + r")\b)",
    re.IGNORECASE,
)

_CLAUSE_STARTS_WITH_VERB_RE = re.compile(
    r"^\s*(?:[-*]|\d+[.)])?\s*(?:" + IMPERATIVE_VERBS + r")\b",
    re.IGNORECASE,
)

_ENUM_LINE_RE = re.compile(r"^\s*(?:[-*]|\d+[.)])\s+\S", re.MULTILINE)


def _is_decomposable(prompt: str) -> bool:
    clauses = _CLAUSE_SPLIT_RE.split(prompt)
    verb_clause_count = sum(
        1 for c in clauses if _CLAUSE_STARTS_WITH_VERB_RE.match(c)
    )
    enum_line_count = len(_ENUM_LINE_RE.findall(prompt))
    return verb_clause_count >= 2 or enum_line_count >= 2


# ---------------------------------------------------------------------------
# Nudge message
# ---------------------------------------------------------------------------

NUDGE = """
[DELEGATION CHECK — multiple subtasks detected]
This prompt looks decomposable into independent subtasks. Before executing:
  1. Split the work into independent subtasks.
  2. Dispatch every independent subtask as a separate `Agent` call in this
     same turn so they run in parallel — see ~/.claude/rules/delegation.md
     (user-level file, not project-relative).
  3. Pick model + effort per subtask from the matrix in that file.
  4. Keep interdependent, interactive, or trivial context-bound work inline.
Skip delegation only when a subtask needs a sibling's result, needs to ask
the user a question, or is cheaper to just do directly.
"""


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def _sweep_stale_markers(threshold_seconds: int = 3600) -> None:
    cutoff = time.time() - threshold_seconds
    for m in Path(tempfile.gettempdir()).glob("cc-delegate-nudge-*.lock"):
        try:
            if m.stat().st_mtime < cutoff:
                m.unlink(missing_ok=True)
        except OSError:
            pass


def main() -> None:
    if os.environ.get("ICO_NO_DELEGATE_NUDGE"):
        sys.exit(0)

    _sweep_stale_markers()

    prompt: str = data.get("prompt", "")
    if not prompt:
        sys.exit(0)

    if not _is_decomposable(prompt):
        sys.exit(0)

    # Dedup marker in case this hook is ever registered more than once for
    # the same prompt (mirrors convention-loader.py's pattern).
    session_id = data.get("session_id", "")
    if session_id:
        prompt_hash = hashlib.md5(prompt.encode("utf-8", errors="replace")).hexdigest()[:8]
        marker = Path(tempfile.gettempdir()) / f"cc-delegate-nudge-{session_id}-{prompt_hash}.lock"
        if marker.exists():
            sys.exit(0)
        try:
            marker.touch()
        except OSError:
            pass  # never crash over a marker write failure

    print(NUDGE)
    sys.exit(0)


if __name__ == "__main__":
    main()
