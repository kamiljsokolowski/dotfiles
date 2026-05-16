---
name: git-commit
description: Create a Git commit for currently staged changes with an auto-generated conventional commit message. Use when the user asks to commit, save work, or create a checkpoint of staged changes.
disable-model-invocation: false
allowed-tools: Bash(git status) Bash(git diff *) Bash(git log *) Bash(git add *) Bash(git commit *)
argument-hint: "[--yes]"
---

# git-commit

## Step 1 — Collect all changes

```bash
git status --short
```

**Tracked changes** (lines where the second character is `M`, `D`, or `R`) — list them and ask:

> "The following tracked changes were found — press Enter to stage all, or enter numbers to
> exclude (comma-separated):
>
> 1. modified: path/to/file
> 2. deleted:  path/to/other
> …"

If the user presses Enter, run `git add -u`. Otherwise stage only the non-excluded files
individually (`git add <file>`). Files the user excludes are left unstaged — do not warn or retry.

**Untracked files** (`??` lines) — do NOT auto-stage. Pre-existing untracked files may have
existed before the session and are unrelated to the current work. Instead, list them and ask:

> "The following untracked files were found — enter the numbers to include (comma-separated),
> or press Enter to skip all:
>
> 1. path/to/file
> 2. path/to/other
> …"

Stage only the confirmed ones individually (`git add <file>`).

Then verify there is something staged:

```bash
git diff --cached --stat
```

If output is still empty: inform the user that there is nothing to commit and stop.

## Step 2 — Read the diff and recent history

Run both before generating anything:

```bash
git diff --cached          # full diff for message generation
git log --oneline -5       # recent commits for style/scope context
```

## Step 3 — Generate the commit message

Use this template:

```text
<type>[(<scope>)]: <description>

[body]

[footer]
```

### Type selection

| Type       | Use when the diff shows…                                        |
|------------|------------------------------------------------------------------|
| `feat`     | New capability, endpoint, flag, or behavior exposed to callers  |
| `fix`      | Corrects incorrect behavior or broken logic                     |
| `perf`     | Same behavior, measurably faster or cheaper                     |
| `refactor` | Restructured code — no behavior change, no bug fix              |
| `test`     | Tests added or corrected; no production code change             |
| `docs`     | Comments, READMEs, docstrings only                              |
| `ci`       | Pipeline, workflow, Dockerfile, Makefile targets                |
| `build`    | Dependency changes, build system config                         |
| `chore`    | Maintenance that fits none of the above                         |

If the diff clearly breaks callers or changes a public contract: append `!` after type/scope and add a `BREAKING CHANGE:` footer.

### Scope

Use the most affected module, package, or subdirectory. Omit if the change is genuinely cross-cutting. Use lowercase, hyphen-separated: `auth`, `http-client`, `storage`.

### Description rules

- Imperative mood: "add", "fix", "remove" — not "added" / "adds"
- No period at end
- No longer than 72 characters
- Lowercase after the colon

### Body

Include when the *why* is not obvious from the description. Omit otherwise — do not pad.

### Footer

Only include footers that apply:

- `BREAKING CHANGE: <explanation>` — incompatible API/behavior change
- `Refs: #<number>` — if an issue number is visible in the diff (e.g., in comments or branch name)
- `Co-authored-by: Name <email>` — if relevant

## Step 4 — Commit

**If `$ARGUMENTS` contains `--yes`**: commit immediately without asking.

```bash
git commit -m "<message>"   # use -m for single-line; use heredoc for multi-line
```

**Otherwise** (default — including all user-triggered invocations):

Run `git diff --cached --name-status` and show the file list together with the proposed message,
then ask for confirmation. Format:

```text
Files to be committed:
  M  path/to/file1
  D  path/to/file2

---
<proposed commit message>
```

Commit this? `[y]` yes / `[n]` cancel / `[e]` edit

The file list is shown to the user for review but is **not** included in the `git commit -m` message.

- `y` → run `git commit` with the message as shown
- `n` → abort; inform the user nothing was committed
- `e` → ask the user what to change, apply their correction, commit with the revised message

For multi-line messages, use a heredoc to preserve formatting:

```bash
git commit -m "$(cat <<'EOF'
feat(auth): replace session cookies with JWTs

Removes session store dependency. Clients receive 401 with
WWW-Authenticate header on token expiry.

BREAKING CHANGE: existing sessions invalidated on deploy
EOF
)"
```
