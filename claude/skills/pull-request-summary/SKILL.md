---
name: pull-request-summary
description: Generate a reviewer-facing PR description from the current branch diff
disable-model-invocation: true
allowed-tools: Bash(git *), Bash(gh *), Bash(bbctl *), Read, Grep, Glob
argument-hint: "[base-branch] [--skip-sandbox]"
---

## Step 1 — Pre-flight

Verify inside a git repo:

```bash
git rev-parse --is-inside-work-tree 2>/dev/null
```

If fails: "Not inside a git repository." Stop.

Get current branch:

```bash
git branch --show-current
```

If empty output: "Detached HEAD — check out a named branch and retry." Stop.

Store as CURRENT_BRANCH.

## Step 2 — Resolve base branch

Parse $ARGUMENTS:
- The first token that does not start with `--` is the base branch override.
- If `--skip-sandbox` is present, store SKIP_SANDBOX=true; otherwise SKIP_SANDBOX=false.

**If base branch provided via $ARGUMENTS:** validate it exists:

```bash
git show-branch <base> 2>/dev/null || git ls-remote --heads origin <base> | grep -q .
```

If neither resolves: "Base branch '<base>' not found locally or on origin." Stop.

**Otherwise resolve automatically (try in order, stop at first result):**

1. `gh repo view --json defaultBranchRef --jq '.defaultBranchRef.name' 2>/dev/null`
2. `git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@'`
3. Name probe — check `main`, then `master`, then `develop` via `git show-branch <name> 2>/dev/null`
4. If all fail: "Could not determine base branch. Run `/pull-request-summary <base-branch>` with an explicit branch." Stop.

Store as BASE_BRANCH.

If CURRENT_BRANCH == BASE_BRANCH: "You appear to be on the default branch (`BASE_BRANCH`). Run this from a feature branch." Stop.

## Step 3 — Scope analysis

Run all three and store output:

```bash
git log --oneline $BASE_BRANCH..$CURRENT_BRANCH          # commit list
git diff --stat $BASE_BRANCH..$CURRENT_BRANCH | tail -1  # totals line
git diff --name-only $BASE_BRANCH..$CURRENT_BRANCH       # file paths
```

If git log is empty: "No commits found between `$BASE_BRANCH` and `$CURRENT_BRANCH`. Check that the base branch is correct." Stop.

**Compute from the file list:**

- File count (raw)
- LOC changed (from --stat totals line)
- Unique top-level directories: `git diff --name-only ... | sed 's|/.*||' | sort -u`
- Exclude from LOC counts: paths matching `vendor/`, `node_modules/`, `*.pb.go`, `*_generated.*`, `*.lock`, `go.sum`

**Emit scope warnings before generating the description, if any apply:**

- Files > 20 or net LOC > 500: "⚠ Large PR — consider splitting by layer or domain."
- Unique top-level directories > 2: "⚠ Mixed domains — likely a split candidate."
- Diff contains migration file AND non-migration changes (detect: `migrations/`, `*.sql`, `*.migration.*`): "⚠ Migration + feature in one PR — these should be separate PRs."

## Step 4 — Full diff analysis

```bash
git diff $BASE_BRANCH..$CURRENT_BRANCH
```

Infer from the diff:

- **Type:** `feat` (new capability) | `fix` (bug) | `refactor` (no behavior change) | `chore` (deps/tooling/build) | `docs` | `test` | `perf` | `ci`
- **Scope:** single logical domain from dominant file paths (e.g., `auth`, `api`, `storage`, `infra`)
- **Test coverage present:** any test files (`*_test.*`, `*.spec.*`, `tests/`, `__tests__/`) in diff
- **Breaking changes:** removed exports, changed function signatures, schema column removal, deprecated API removal
- **Issue reference:** scan branch name (CURRENT_BRANCH) and commit messages for `#NNN`, `DT-NNN`, `PROJ-NNN` patterns

If commit messages are low-quality (contain only "wip", "fix", "update", "changes"), derive title and summary from diff content — not message text.

## Step 5 — Generate PR description

**Title** — imperative mood, max 72 chars for the conventional commit part:

```
<type>(<scope>): <verb> <object>

# Examples:
feat(auth): add OAuth2 PKCE flow for CLI clients
fix(mesh-client): add exponential backoff retry to HTTP client
refactor(storage): extract S3 client into reusable module
chore(deps): bump controller-runtime to v0.17.2
```

If SKIP_SANDBOX=true, prepend `[SKIP_SANDBOX_CREATION] ` to the title:

```
[SKIP_SANDBOX_CREATION] feat(auth): add OAuth2 PKCE flow for CLI clients
```

**Body** — omit any section entirely if it has no content. Never write "N/A", "None", or leave placeholder text:

```markdown
## Summary
One paragraph: what changed and what it does. Write for a reviewer who hasn't seen the diff.

## Motivation
Why this change exists. Include issue/ticket reference if found (Closes #N).

## Approach
Non-obvious decisions and tradeoffs only. Bullet list. No line-by-line walkthrough.

## Test Plan
Checkbox list. Scope each item. If no test files were in the diff, write:
"- [ ] No automated test changes — manual verification required: [describe steps]"

## Breaking Changes
Only if present. Omit section entirely if none.

## Reviewer Focus
Specific files/lines/decisions to highlight. Omit if nothing specific to call out.
```

## Step 6 — Output and PR creation

Print the complete PR description as a fenced markdown block.

Then detect remote platform:

```bash
git remote get-url origin 2>/dev/null
```

**If URL contains `github.com`:** ask: "Create this PR on GitHub? (yes/no)"

- If yes, run:

```bash
gh pr create \
  --title "<generated title>" \
  --body "$(cat <<'EOF'
<generated body>
EOF
)"
```

- If `gh` is not installed or `gh auth status` fails: note it and skip.

**If URL contains `bitbucket`:** ask: "Create this PR on Bitbucket? (yes/no)"

- Extract project and repo from the remote URL:

```bash
# Handles HTTPS (https://host/scm/PROJECT/REPO.git)
# and SSH (ssh://git@host:PORT/PROJECT/REPO.git) formats
REMOTE_URL=$(git remote get-url origin)
BBCTL_PROJECT=$(echo "$REMOTE_URL" | sed 's|.*[/:]scm[/:]||;s|/.*||' 2>/dev/null \
  || echo "$REMOTE_URL" | sed 's|.*/\([^/]*\)/[^/]*\.git$|\1|')
BBCTL_REPO=$(echo "$REMOTE_URL" | sed 's|.*/||;s|\.git$||')
```

- Then run:

```bash
bbctl pr create \
  --title "<generated title>" \
  --body "<generated body>" \
  --project "$BBCTL_PROJECT" \
  --repo "$BBCTL_REPO" \
  --target "$BASE_BRANCH"    # explicit target; don't rely on repo default
```

- If `bbctl` is not installed: note it and skip.

**If URL is neither or no remote exists:** print the description only.
