---
name: bash-scripting
description: >
  Use this skill whenever the user asks to write, review, refactor, audit, or
  generate bash or shell scripts. Triggers include: any mention of .sh files,
  shell scripting, bash automation, CI/CD shell steps, cron jobs, startup
  scripts, wrapper scripts, or requests phrased as "write a script to...",
  "create a shell script", "help me with this bash", or "review my script".
  Also trigger when a user pastes a shell script and asks for improvements,
  bug fixes, or a code review. Apply these standards unconditionally — even
  for short one-off utility scripts. Do NOT apply for Python, Ruby, Go, or
  other non-shell languages, even if they invoke shell commands.
---

# Bash Scripting — Best Practices Skill

Apply all rules in this skill when writing, reviewing, or refactoring bash scripts.
For detailed reference material, see `references/standards.md`.

## Environment Detection

Detect whether running in CLI (Claude Code) or chat mode and adapt tool usage accordingly:

- **CLI mode (Claude Code):** always prefer local tools for linting, formatting, and syntax
  checks over asking Claude to reason about correctness. Run tools, show output, fix issues.
- **Chat mode:** Claude reviews code directly and flags issues inline.

In CLI mode the toolchain below is the source of truth — not Claude's static analysis.

## Local Toolchain (CLI Mode)

See `references/tools.md` for full install instructions and config snippets.

| Tool | Role | Key command |
|---|---|---|
| `shellcheck` | Static analysis / linter — **mandatory** | `shellcheck script.sh` |
| `shfmt` | Formatter (Google style flag: `-i 2 -ci -bn`) | `shfmt -d script.sh` |
| `bash -n` | Syntax check (fast, no execution) | `bash -n script.sh` |
| `bats` | Unit / integration testing | `bats tests/` |

**Workflow in CLI mode:**
1. Write or edit script
2. `bash -n script.sh` — catch syntax errors first (fast)
3. `shellcheck script.sh` — fix all warnings before proceeding
4. `shfmt -d script.sh` — check formatting drift; use `-w` to auto-fix
5. `bats tests/` — run tests if present
6. Only after all tools pass — commit or present to user

**Never skip step 3** to save time. ShellCheck catches entire classes of bugs that are
invisible to syntax checkers and runtime testing.

## Non-Negotiable Output Contract

Every script produced MUST satisfy all of these — no exceptions for "short" or "simple" scripts:

1. Starts with `#!/usr/bin/env bash` + `set -euo pipefail`
2. Has a file header comment block (description, usage, dependencies)
3. Uses `main "$@"` pattern for any script with more than one logical step
4. Routes all errors through `err()` to stderr — never bare `echo` for errors
5. Passes `shellcheck` with zero warnings (verified locally in CLI mode)
6. Passes `shfmt -d` with no diff (formatted to Google style)
7. Any intentional deviation from standards is commented inline with justification

## Quick Reference

| Concern | Rule |
|---|---|
| Shebang | `#!/usr/bin/env bash` |
| Safety flags | `set -euo pipefail` |
| Tests | `[[ ]]` always, never `[ ]` |
| Arithmetic | `(( ))` or `$(( ))`, never `expr` or `$[ ]` |
| Command sub | `$()` always, never backticks |
| Variables | Always quoted: `"${var}"` |
| Lists | Arrays, never space-delimited strings |
| Loops over cmd output | Process substitution `< <(cmd)`, never `cmd \| while` |
| Naming: globals/constants | `UPPER_SNAKE_CASE` + `readonly` |
| Naming: locals | `lower_snake_case` + `local` |
| Wildcard expansion | `./*` not `*` |
| Error output | `>&2` always |
| Cleanup | `trap 'cleanup' EXIT` |
| Dependency check | `command -v tool` upfront |

## Canonical Script Template

```bash
#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# Script: <name>.sh
# Description: <What this does, one or two sentences>
# Usage: ./<name>.sh [OPTIONS] <args>
# Dependencies: <non-standard tools required, e.g. jq, curl>
# -----------------------------------------------------------------------------
set -euo pipefail

# -- Constants ----------------------------------------------------------------
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly SCRIPT_NAME="$(basename "$0")"

# -- Logging ------------------------------------------------------------------
log() { echo "[$(date +'%Y-%m-%dT%H:%M:%S%z')] INFO:  $*"; }
err() { echo "[$(date +'%Y-%m-%dT%H:%M:%S%z')] ERROR: $*" >&2; }

# -- Cleanup ------------------------------------------------------------------
readonly TMP_DIR="$(mktemp -d)"
trap 'rm -rf "${TMP_DIR}"' EXIT

# -- Dependencies -------------------------------------------------------------
#######################################
# Verify required external tools are available.
# Globals: None
# Arguments: None
# Returns: 1 if any dependency missing
#######################################
check_deps() {
  local deps=( curl jq )  # adjust as needed
  local missing=0
  for dep in "${deps[@]}"; do
    command -v "${dep}" &>/dev/null || { err "Missing dependency: ${dep}"; missing=1; }
  done
  (( missing == 0 )) || exit 1
}

# -- Usage --------------------------------------------------------------------
usage() {
  cat <<EOF
Usage: ${SCRIPT_NAME} [-h] [-v] [-f FILE]

Options:
  -h        Show this help and exit
  -v        Enable verbose output
  -f FILE   Input file (required)
EOF
}

# -- Argument Parsing ---------------------------------------------------------
VERBOSE=false
INPUT_FILE=""

parse_args() {
  while getopts "hvf:" opt; do
    case "${opt}" in
      h) usage; exit 0 ;;
      v) VERBOSE=true ;;
      f) INPUT_FILE="${OPTARG}" ;;
      *) usage; exit 1 ;;
    esac
  done
  shift $(( OPTIND - 1 ))

  [[ -n "${INPUT_FILE}" ]] || { err "-f FILE is required"; usage; exit 1; }
}

# -- Core Logic ---------------------------------------------------------------
#######################################
# Main entry point.
# Globals:
#   INPUT_FILE, VERBOSE
# Arguments:
#   All script arguments via "$@"
#######################################
main() {
  parse_args "$@"
  check_deps
  log "Starting ${SCRIPT_NAME}"

  # TODO: implement logic here

  log "Done."
}

main "$@"
```

## Key Patterns to Always Apply

### Error handling
```bash
# Fail fast with message
cmd || { err "cmd failed"; exit 1; }

# Intentional ignore — must comment why
rm -f /tmp/lock || true  # Non-critical cleanup
```

### Safe loop over command output (subshell variable scope)
```bash
# Good — variables visible after loop
while IFS= read -r line; do
  process "${line}"
done < <(some_command)

# Bad — last_line always empty after loop due to subshell
some_command | while read -r line; do last_line="${line}"; done
```

### Arrays for argument lists
```bash
declare -a flags=( --foo --bar="baz" )
flags+=( --extra )
mybinary "${flags[@]}"  # Never: mybinary ${flags}
```

### Arithmetic
```bash
if (( count > threshold )); then ...   # Good
if [[ "${count}" -gt "${threshold}" ]]; then ...  # Also OK
if [[ "${count}" > "${threshold}" ]]; then ...    # BAD — lexicographic
```

## ShellCheck Compliance

- Zero warnings is the target — not a goal
- Suppressions require inline justification:
```bash
# shellcheck disable=SC2086  # Intentional word-split for dynamic flag expansion
eval "${dynamic_cmd}"
```
- Avoid `eval` entirely unless no alternative exists

## When to Suggest Moving Beyond Bash

Flag when a script should be rewritten in Python/Go/etc:
- Logic exceeds ~100 lines
- Requires associative arrays or complex data structures
- Heavy string manipulation / parsing
- Performance is a concern
- Error handling complexity is growing

## References

- `references/standards.md` — full rules, rationale, edge cases, BashFAQ links
- `references/tools.md` — local toolchain install, config, and CI integration
