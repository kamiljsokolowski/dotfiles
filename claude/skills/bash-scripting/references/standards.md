# Bash Scripting Standards — Full Reference

Sources:
- Google Shell Style Guide: https://google.github.io/styleguide/shellguide.html
- ShellCheck: https://www.shellcheck.net / https://github.com/koalaman/shellcheck/wiki
- BashFAQ (Greg's Wiki): https://mywiki.wooledge.org/BashFAQ
- BashPitfalls: https://mywiki.wooledge.org/BashPitfalls
- Bash Strict Mode rationale: http://redsymbol.net/articles/unofficial-bash-strict-mode/

---

## 1. Shebang & Safety Flags

```bash
#!/usr/bin/env bash
set -euo pipefail
```

| Flag | Meaning |
|---|---|
| `set -e` | Exit immediately on unhandled non-zero exit |
| `set -u` | Treat unset variables as errors |
| `set -o pipefail` | Pipe fails if any segment fails, not just the last |
| `#!/usr/bin/env bash` | Portable — finds bash in PATH, not hardcoded `/bin/bash` |

Optional debug line (leave commented in production):
```bash
# set -x  # Trace all executed commands to stderr
```

**Why not `#!/bin/bash`?** On macOS, NixOS, and some container images bash lives
elsewhere. `env bash` is portable. Google style allows either; prefer `env bash`
for scripts that run across environments.

---

## 2. File Header

Every script requires:

```bash
#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# Script: deploy.sh
# Description: Rolls out a new version to GKE and waits for rollout health.
# Usage: ./deploy.sh [-e ENV] [-t TAG] [-h]
# Dependencies: kubectl, gcloud, jq
# -----------------------------------------------------------------------------
set -euo pipefail
```

Copyright and author are optional (Google style), but recommended for shared scripts.

---

## 3. Function Comments (Google docblock)

Required for any non-trivial function and ALL library functions:

```bash
#######################################
# Brief one-line summary.
# Globals:
#   BACKUP_DIR     (read)
#   LAST_ERROR     (write)
# Arguments:
#   $1 - Source path (string)
#   $2 - Destination path (string)
# Outputs:
#   Writes progress to stdout
#   Writes errors to stderr
# Returns:
#   0 on success
#   1 on missing argument
#   2 on copy failure
#######################################
function copy_with_verify() {
  local src="${1:?'source path required'}"
  local dst="${2:?'destination path required'}"
  ...
}
```

---

## 4. Naming Conventions

| Type | Convention | Declaration |
|---|---|---|
| Global / env vars | `UPPER_SNAKE_CASE` | `readonly MY_VAR="value"` |
| Local function vars | `lower_snake_case` | `local my_var="value"` |
| Constants | `UPPER_SNAKE_CASE` | `readonly MAX_RETRY=3` |
| Functions | `lower_snake_case` | `function my_func() {` |
| Script files | `kebab-case.sh` or no extension | — |
| Library files | `kebab-case.sh` (not executable) | — |

**Always use `local`** inside functions. Leaking into global scope is a common source of bugs.

```bash
# Bad — modifies global 'i'
function process() {
  for i in "$@"; do echo "${i}"; done
}

# Good
function process() {
  local item
  for item in "$@"; do echo "${item}"; done
}
```

---

## 5. Quoting Rules

**Default: always quote.**

```bash
# Variables — always brace + quote
echo "${my_var}"          # Good
echo "$my_var"            # Tolerated, not preferred
echo $my_var              # Bad — word splitting, glob expansion

# Command substitutions — always quote
result="$(some_cmd)"      # Good
result=$(some_cmd)        # Bad — trailing newlines stripped, splitting risk

# Arrays — always use [@] with quotes
cmd "${args[@]}"          # Good — each element as separate word
cmd "${args[*]}"          # Bad — all elements as single word
cmd ${args[@]}            # Bad — no quoting

# Positional args — "$@" not "$*"
pass_through "$@"         # Good — preserves original word boundaries
pass_through "$*"         # Bad — joins all args into one string
```

**Single quotes** for literal strings with no substitution:
```bash
echo 'literal $PATH and $(cmd) — not expanded'
grep -P '^\d+\s+\w+$' file  # Regex: single quotes prevent shell interpretation
```

**Pattern matching in `[[ ]]`** — right side must NOT be quoted for glob/regex:
```bash
if [[ "${filename}" == *.log ]]; then ...    # Good — glob
if [[ "${filename}" == "*.log" ]]; then ...  # Bad — literal string match
if [[ "${str}" =~ ^[0-9]+$ ]]; then ...      # Good — regex, unquoted RHS
```

---

## 6. Tests and Conditionals

**Always use `[[ ]]` over `[ ]` or `test`.**

`[[ ]]` advantages:
- No word splitting or pathname expansion inside
- Supports `==` with glob patterns
- Supports `=~` for regex
- Supports `&&` and `||` without escaping

```bash
# String tests
if [[ -z "${var}" ]]; then ...         # empty string
if [[ -n "${var}" ]]; then ...         # non-empty string
if [[ "${var}" == "expected" ]]; then  # equality (use ==, not =)
if [[ "${var}" != "other" ]]; then     # inequality

# File tests
if [[ -f "${path}" ]]; then ...   # regular file exists
if [[ -d "${path}" ]]; then ...   # directory exists
if [[ -r "${path}" ]]; then ...   # readable
if [[ -x "${path}" ]]; then ...   # executable

# Numeric comparisons — use (( )) or -lt/-gt, never < > inside [[ ]]
if (( count > 10 )); then ...
if [[ "${count}" -gt 10 ]]; then ...
if [[ "${count}" > 10 ]]; then ...   # BAD — lexicographic: "9" > "10" is TRUE
```

---

## 7. Arrays vs Strings

**Use arrays for any list of values, especially command arguments.**

The core problem with strings:
```bash
# This breaks with spaces in filenames or values
files="file1.txt file with spaces.txt file3.txt"
for f in ${files}; do rm "${f}"; done  # Splits on spaces — broken

# Correct
declare -a files=( "file1.txt" "file with spaces.txt" "file3.txt" )
for f in "${files[@]}"; do rm "${f}"; done
```

Building argument arrays:
```bash
declare -a cmd_args=( --output="${outdir}" --verbose )
[[ "${dry_run}" == true ]] && cmd_args+=( --dry-run )
run_tool "${cmd_args[@]}"
```

Reading lines into array (bash 4+):
```bash
readarray -t lines < <(some_command)
for line in "${lines[@]}"; do
  process "${line}"
done
```

**Never** use `declare -a files=($(ls /dir))` — word splits on whitespace and
expands globs unpredictably. Use `readarray` + process substitution instead.

---

## 8. Loops & Process Substitution

The classic subshell trap:
```bash
# BAD — pipe creates subshell; last_line is always empty after loop
last_line="NULL"
some_command | while IFS= read -r line; do
  last_line="${line}"
done
echo "${last_line}"  # Always "NULL"

# GOOD — process substitution; while runs in current shell
last_line="NULL"
while IFS= read -r line; do
  last_line="${line}"
done < <(some_command)
echo "${last_line}"  # Correct value

# ALSO GOOD — readarray (bash 4+)
readarray -t lines < <(some_command)
```

**`IFS= read -r`** is the canonical safe read pattern:
- `IFS=` prevents leading/trailing whitespace stripping
- `-r` prevents backslash interpretation

**`for` over command output** — only safe when output is guaranteed whitespace-free:
```bash
# Risky — splits on whitespace
for f in $(ls /dir); do ...

# Safe — glob expansion, no subshell
for f in /dir/*; do ...

# Safe — controlled newline-split via readarray
readarray -t items < <(generate_items)
for item in "${items[@]}"; do ...
```

---

## 9. Arithmetic

```bash
# Good — (( )) for statements
(( count++ ))
(( total = a + b ))

# Good — $(( )) for expressions in strings/assignments
echo "Total: $(( a + b ))"
readonly TIMEOUT=$(( BASE_TIMEOUT * 2 ))

# Bad — legacy, avoid
let count++          # avoid 'let'
count=$[ $a + $b ]   # deprecated syntax
count=$(expr $a + $b) # spawns subprocess unnecessarily
```

**Caution with `set -e` and `(( ))`:** an arithmetic expression evaluating to 0
is a non-zero exit — `set -e` will kill the script:

```bash
set -e
i=0
(( i++ ))  # i becomes 1, but expression returns 0 — exits!

# Fix: use || true, or check explicitly
(( i++ )) || true
(( ++i ))   # pre-increment: expression value is 1 if i was 0
```

---

## 10. Command Substitution

```bash
# Good
result="$(command "$(inner_command)")"

# Bad — backticks require escaping inner quotes
result="`command \`inner_command\``"
```

Always quote command substitutions to preserve newlines and prevent word splitting.

---

## 11. Pipelines

Single-line if it fits:
```bash
grep "pattern" file | sort | uniq
```

Multi-line: pipe at start of continuation line, 2-space indent:
```bash
grep "ERROR" "${log_file}" \
  | awk '{print $5}' \
  | sort \
  | uniq -c \
  | sort -rn \
  > "${report_file}"
```

---

## 12. `eval` — Avoid

`eval` executes arbitrary strings as code. Nearly always avoidable:

```bash
# Bad — eval with dynamic content is a code injection vector
eval "$(generate_flags)"

# Better — use arrays
declare -a flags
readarray -t flags < <(generate_flags)
mycmd "${flags[@]}"
```

When `eval` is truly the only option, suppress ShellCheck and comment why:
```bash
# shellcheck disable=SC2086
# Rationale: dynamic flag string from trusted config, array not viable here
eval "${trusted_flags}"
```

---

## 13. Wildcard Expansion

Files starting with `-` are interpreted as flags by many commands:

```bash
rm *          # rm -rf / if a file named '-rf' exists — catastrophic
rm ./*        # Safe — ./ prefix prevents flag interpretation

for f in *; do ...    # Risky
for f in ./*; do ...  # Safe
```

---

## 14. SUID/SGID

Never set SUID or SGID on shell scripts. Use `sudo` for privilege escalation.

---

## 15. Dependency Checking

Check all non-standard tools at script start, before doing any work:

```bash
check_deps() {
  local deps=( kubectl jq gcloud )
  local missing=0
  for dep in "${deps[@]}"; do
    command -v "${dep}" &>/dev/null || {
      err "Required tool not found: ${dep}"
      missing=1
    }
  done
  (( missing == 0 )) || { err "Install missing dependencies and retry."; exit 1; }
}
```

---

## 16. Cleanup with `trap`

Always clean up temp files even on failure:

```bash
readonly TMP_DIR="$(mktemp -d)"
readonly TMP_FILE="$(mktemp)"
trap 'rm -rf "${TMP_DIR}" "${TMP_FILE}"' EXIT

# For more complex cleanup
cleanup() {
  local exit_code=$?
  rm -rf "${TMP_DIR}"
  [[ $exit_code -ne 0 ]] && err "Script failed with exit code ${exit_code}"
}
trap cleanup EXIT
```

`EXIT` fires on any exit including errors, signals, and normal completion.

---

## 17. Script-Relative Paths

Never assume working directory. Use `BASH_SOURCE[0]`:

```bash
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source library relative to script
source "${SCRIPT_DIR}/lib/utils.sh"

# Reference data file relative to script
config_file="${SCRIPT_DIR}/config/defaults.yaml"
```

---

## 18. Argument Parsing Patterns

### Simple (getopts — POSIX, short flags only)
```bash
usage() {
  cat <<EOF
Usage: $(basename "$0") [-h] [-v] [-e ENV] [-t TAG]
  -h        Help
  -v        Verbose
  -e ENV    Target environment (default: staging)
  -t TAG    Docker image tag (required)
EOF
}

VERBOSE=false
ENV="staging"
TAG=""

while getopts "hve:t:" opt; do
  case "${opt}" in
    h) usage; exit 0 ;;
    v) VERBOSE=true ;;
    e) ENV="${OPTARG}" ;;
    t) TAG="${OPTARG}" ;;
    *) usage >&2; exit 1 ;;
  esac
done
shift $(( OPTIND - 1 ))

[[ -n "${TAG}" ]] || { err "-t TAG is required"; usage >&2; exit 1; }
```

### Long flags
`getopts` doesn't support long flags natively. Options:
- Manual `case` loop over `$@`
- `getopt` (GNU, not portable to macOS without brew)
- Consider Python/Go if arg parsing is complex

---

## 19. Builtins vs External Commands

Prefer builtins — no subprocess fork:

```bash
# String contains check
if [[ "${str}" == *"substr"* ]]; then ...    # builtin, fast
if echo "${str}" | grep -q "substr"; then ... # spawns grep

# String length
if [[ ${#var} -gt 10 ]]; then ...            # builtin
if [[ $(echo -n "${var}" | wc -c) -gt 10 ]]  # spawns wc

# Default values
name="${1:-default}"                          # builtin parameter expansion
name=$([ -z "$1" ] && echo "default" || echo "$1")  # ugly, slow
```

---

## 20. When to Stop Writing Bash

Rewrite in Python/Go when any of these apply:
- Script exceeds ~100 lines of logic
- Needs associative arrays (bash 4 only, fragile)
- Heavy string parsing / regex beyond simple greps
- Complex data structures
- Performance matters
- Error handling is growing in complexity
- The script is becoming difficult to test

> "If performance matters, use something other than shell." — Google Shell Style Guide

---

## Additional Resources

| Resource | URL | When to consult |
|---|---|---|
| Google Shell Style Guide | https://google.github.io/styleguide/shellguide.html | Formatting, naming, structure |
| ShellCheck Wiki | https://github.com/koalaman/shellcheck/wiki | SC-code explanations |
| BashFAQ | https://mywiki.wooledge.org/BashFAQ | Canonical gotcha explanations |
| BashPitfalls | https://mywiki.wooledge.org/BashPitfalls | 60+ common mistakes with fixes |
| Bash Strict Mode | http://redsymbol.net/articles/unofficial-bash-strict-mode/ | Rationale for set -euo pipefail |
| Bash Manual | https://www.gnu.org/software/bash/manual/ | Authoritative reference |
