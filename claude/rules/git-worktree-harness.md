# Git Worktree & Protected-Branch Harness

This is the *behavioral* half of a two-layer safety net. The *mechanical*
half is `~/.claude/hooks/git-guard.py`, a `PreToolUse`/`Bash` hook that
hard-blocks violations at execution time by reading each repo's live
`git rev-parse` state. This doc is the primary steer — proactively follow it
so the hook never has to fire.

## Rules

1. **Feature work always happens in a worktree.** Before starting any
   feature/fix branch, run `git worktree add ../<name> -b <branch>` from the
   primary clone rather than `git switch -c` / `git checkout -b` in place.
   Branch creation attempted directly in the primary clone is hard-blocked.
   The branch name you pass to `-b` must follow the naming convention below
   — see **Branch Naming**.

2. **Never commit directly to `main`/`master`.** No `git commit`
   (including `--amend`), no local `git merge` into a protected branch, no
   `git reset --hard` on one, no force-push (`--force` /
   `--force-with-lease` / `-f`) targeting one. All are hard-blocked
   regardless of repo.

3. **Each repo is an independent, protected scope.** When work spans
   multiple repos in one session, evaluate and act on each repo's own live
   branch/worktree state — a decision made for repo A never carries over to
   repo B. The hook enforces this automatically (it resolves state per
   `cwd`/`-C`/`cd` at the moment of each command), but keep the same
   discipline when reasoning about multi-repo work: don't assume "we're on a
   feature branch" carries across a `cd` into a different repo.

4. **The only sanctioned override is `GIT_GUARD_OFF=1`.** If a legitimate
   case requires bypassing the guard (rare — e.g. a scripted rebase inside a
   throwaway scratch clone), set it explicitly for that one command and
   surface to the user that you did so and why. Never reach for it to route
   around a block without explaining first — a block from this hook usually
   means the request or approach needs reconsidering, not silencing.

## Branch Naming

Branch names follow [conventionalbranch.org](https://conventionalbranch.org/):
`<type>/<kebab-description>`, e.g. `feature/add-ingest-retry`.

- **Allowed types (permissive superset):** `feature`, `bugfix`, `hotfix`,
  `release`, `chore`, `fix`, `docs`. This is a superset of the strict spec —
  `fix` and `docs` are included so it doesn't collide with per-project
  conventions (e.g. `ico-ai-tooling`'s GitHub repos use `fix/`).
- Uppercase is tolerated in the description segment to accommodate ticket
  IDs — e.g. `feature/CLIN-12345-add-widget` — a deliberate deviation from
  the strict spec's all-lowercase rule.
- A project's own rules may impose a **stricter** form on top (e.g. CLIN's
  `feature/CLIN-XXXXX-descriptive-name` requirement) — the global check here
  only enforces shape and type, not project-specific content.
- Enforced by `git-guard.py` on every branch-creating command (`worktree add
  -b`, `switch -c`, `checkout -b`, `branch <new>`) — hard-deny, same as the
  rest of this harness. This is the steer so the hook rarely has to fire.

## Why this exists

Direct commits to `main`/`master` and branch creation outside worktrees are
the two mistakes this harness is built to make structurally hard, not just
discouraged. See `~/.claude/hooks/git-guard.py` for the exact detection
logic and `~/.claude/plans/based-on-claude-code-dynamic-hippo.md` for the
design rationale and verification matrix.
