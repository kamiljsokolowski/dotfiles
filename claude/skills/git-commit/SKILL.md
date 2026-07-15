---
name: git-commit
description: Create a Git commit for currently staged changes with an auto-generated conventional commit message. Use when the user asks to commit, save work, or create a checkpoint of staged changes.
disable-model-invocation: false
allowed-tools: Bash(git status) Bash(git diff *) Bash(git log *) Bash(git add *) Bash(git commit *)
argument-hint: "[--yes] [ticket-number]"
---

# git-commit

## Step 0 — Parse arguments

Parse `$ARGUMENTS` before inspecting changes:

- If a token matches a ticket/reference identifier passed in the prompt (for example `PROJ-123`, `DT-456`, or another uppercase project key followed by `-` and digits), store it as PROMPT_TICKET.
- Ignore option tokens such as `--yes` for ticket detection.
- Do not infer PROMPT_TICKET from the branch name or diff for the subject suffix; this suffix is only used when the ticket number was explicitly passed as part of the prompt.

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
- If PROMPT_TICKET is set, append `,ref: <PROMPT_TICKET>` to the first line after the description. Keep the conventional commit description itself within 72 characters before the suffix.

Example with an explicitly passed ticket:

```text
feat(auth): add OAuth2 PKCE flow,ref: PROJ-123
```

### Body

Include when the *why* is not obvious from the description. Omit otherwise — do not pad.

### Footer

Only include footers that apply:

- `BREAKING CHANGE: <explanation>` — incompatible API/behavior change
- `Refs: #<number>` — if an issue number is visible in the diff (e.g., in comments or branch name)
- `Co-authored-by: Name <email>` — for **human** co-authors only (never the AI tool)
- `Assisted-by: <AGENT>:<MODEL> [tool …]` — AI attribution (see below)

### AI attribution & sign-off (Linux kernel guidance)

Per the [kernel AI coding-assistants guidance](https://docs.kernel.org/process/coding-assistants.html):

- This commit is AI-assisted, so add an attribution trailer:
  `Assisted-by: AGENT_NAME:MODEL_VERSION [TOOL …]`
  (e.g. `Assisted-by: Claude Code:claude-opus-4-8`). List only **specialized
  analysis tools** actually used (e.g. `coccinelle`, `sparse`, `smatch`,
  `clang-tidy`); omit basic tools (git, gcc, make, editors).
- The AI tool is recorded with `Assisted-by:` — **never** `Co-authored-by:`
  (that is for human co-authors) and **never** `Signed-off-by:`.
- **Do not add `Signed-off-by` on anyone's behalf.** Only a human can certify
  the Developer Certificate of Origin (DCO). The human submitter is responsible
  for reviewing the generated code, ensuring license compliance (respect the
  project's license; add SPDX identifiers where the project requires them),
  adding their own `Signed-off-by`, and taking full responsibility for the
  contribution.

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
