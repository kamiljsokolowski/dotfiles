# Bash Toolchain — Install, Config & CI

---

## Tool Overview

| Tool | What it catches | Replaces |
|---|---|---|
| `bash -n` | Syntax errors only | Nothing — fastest first check |
| `shellcheck` | Bugs, anti-patterns, quoting issues, SC-codes | Manual code review for correctness |
| `shfmt` | Formatting inconsistencies | Style debates in review |
| `bats` | Runtime behavior, integration paths | ad-hoc manual testing |

Run order matters: `bash -n` → `shellcheck` → `shfmt` → `bats`.
ShellCheck will catch more syntax issues than `bash -n` but is slower to fail.

---

## shellcheck

**What it is:** Static analysis — catches quoting bugs, subshell traps, `[ ]` vs `[[ ]]`,
unset variable risks, SC-coded warnings with explanations.

**Install:**
```bash
# Debian/Ubuntu
apt-get install shellcheck

# macOS
brew install shellcheck

# Alpine (CI containers)
apk add shellcheck

# Standalone binary (pin version for CI reproducibility)
VERSION="v0.10.0"
curl -sSL "https://github.com/koalaman/shellcheck/releases/download/${VERSION}/shellcheck-${VERSION}.linux.x86_64.tar.xz" \
  | tar -xJ --strip-components=1 -C /usr/local/bin shellcheck-${VERSION}/shellcheck
```

**Usage:**
```bash
# Single file
shellcheck script.sh

# All scripts in tree
shellcheck $(find . -name '*.sh' -not -path '*/vendor/*')

# With explicit shell dialect (overrides shebang)
shellcheck --shell=bash script.sh

# JSON output for tooling integration
shellcheck --format=json script.sh

# Exclude specific code (always add inline comment explaining why)
shellcheck --exclude=SC2086 script.sh
```

**Inline suppression** (prefer file-level or function-level if suppressing multiple lines):
```bash
# shellcheck disable=SC2086  # Reason: intentional word-split for dynamic args
some_command ${dynamic_args}

# shellcheck disable=SC1091   # Reason: sourced file generated at runtime
source "${GENERATED_FILE}"
```

**Common SC codes:**
| Code | Issue |
|---|---|
| SC2086 | Unquoted variable — word splitting / glob risk |
| SC2046 | Unquoted command substitution |
| SC2206 | Array assignment from unquoted command substitution |
| SC2181 | Check exit code directly, not via `$?` |
| SC2162 | `read` without `-r` — backslash interpretation |
| SC1091 | Sourced file not found — path not resolvable statically |
| SC2155 | `declare` and assign on same line — masks return value |

Full wiki: https://github.com/koalaman/shellcheck/wiki

---

## shfmt

**What it is:** Formatter — enforces consistent style mechanically. Backed by a proper
shell parser (not regex), so it also catches some syntax errors `bash -n` misses.

**Install:**
```bash
# macOS
brew install shfmt

# Go install (any platform)
go install mvdan.cc/sh/v3/cmd/shfmt@latest

# Standalone binary
VERSION="v3.10.0"
curl -sSL "https://github.com/mvdan/sh/releases/download/${VERSION}/shfmt_${VERSION}_linux_amd64" \
  -o /usr/local/bin/shfmt && chmod +x /usr/local/bin/shfmt
```

**Google style flags:**
```bash
# Check (diff output — use in CI)
shfmt -i 2 -ci -bn -d script.sh

# Auto-fix (write in place)
shfmt -i 2 -ci -bn -w script.sh

# Check entire tree
shfmt -i 2 -ci -bn -d .
```

| Flag | Meaning | Google style? |
|---|---|---|
| `-i 2` | 2-space indent | ✅ |
| `-ci` | Indent `case` branches | ✅ |
| `-bn` | Binary ops (`&&`, `\|`) at start of continuation line | ✅ |
| `-s` | Simplify redundant syntax | Optional |
| `-d` | Diff mode — exit 1 if formatting differs | CI use |
| `-w` | Write in place | Local use |
| `-l` | List files that differ | CI use |

**Project config via `.editorconfig`** (place in repo root — shfmt reads it automatically):
```ini
[*.sh]
indent_style = space
indent_size = 2
shell_variant = bash
binary_next_line = true
switch_case_indent = true
```

Or `.shfmt.toml`:
```toml
shell = "bash"
indent = 2
binary-next-line = true
switch-case-indent = true
```

**Syntax check only** (faster than shellcheck, good for quick gate):
```bash
shfmt script.sh > /dev/null  # exits non-zero on parse error
```

---

## bash -n

Built-in syntax checker. No install needed. Fastest gate — run before shellcheck.

```bash
bash -n script.sh

# Check all scripts
find . -name '*.sh' -exec bash -n {} \;
```

Limitation: only catches syntax errors, not semantic issues. Does not catch quoting bugs,
unset variables, wrong test operators, etc. Always follow up with shellcheck.

---

## bats (Bash Automated Testing System)

**What it is:** TAP-compliant test framework for bash. Write tests in bash-like syntax.
Three companion libraries cover most needs: `bats-assert`, `bats-support`, `bats-file`.

**Install:**
```bash
# macOS
brew install bats-core

# Via git submodule (recommended for CI reproducibility)
git submodule add https://github.com/bats-core/bats-core test/bats
git submodule add https://github.com/bats-core/bats-support test/test_helper/bats-support
git submodule add https://github.com/bats-core/bats-assert test/test_helper/bats-assert
git submodule add https://github.com/bats-core/bats-file test/test_helper/bats-file
```

**Minimal test file (`tests/deploy.bats`):**
```bash
#!/usr/bin/env bats

# Load helpers (adjust path to your submodule layout)
load '../test/test_helper/bats-support/load'
load '../test/test_helper/bats-assert/load'

setup() {
  # Runs before each test
  export TEST_TMP="$(mktemp -d)"
}

teardown() {
  # Runs after each test — always, even on failure
  rm -rf "${TEST_TMP}"
}

@test "script exits 1 when required arg missing" {
  run ./deploy.sh
  assert_failure
  assert_output --partial "required"
}

@test "script creates output file" {
  run ./deploy.sh -f "${TEST_TMP}/input.txt" -o "${TEST_TMP}/output.txt"
  assert_success
  assert_file_exists "${TEST_TMP}/output.txt"
}

@test "script handles spaces in filenames" {
  local input="${TEST_TMP}/file with spaces.txt"
  touch "${input}"
  run ./deploy.sh -f "${input}"
  assert_success
}
```

**Run:**
```bash
bats tests/             # All test files
bats tests/deploy.bats  # Single file
bats --tap tests/       # TAP output for CI
bats --jobs 4 tests/    # Parallel (bats-core 1.7+)
```

**`run` semantics** — key to writing correct tests:
- `run some_command` captures stdout → `$output`, exit code → `$status`
- Does NOT inherit `set -e` — command failure won't abort the test
- Always use `assert_success` / `assert_failure` to check exit code explicitly

---

## pre-commit Integration

Enforce tools automatically on every commit. `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/shellcheck-py/shellcheck-py
    rev: v0.10.0.1
    hooks:
      - id: shellcheck
        args: ["--shell=bash"]

  - repo: https://github.com/nicowillis/pre-commit-shfmt
    rev: v3.10.0
    hooks:
      - id: shfmt
        args: ["-i", "2", "-ci", "-bn", "-d"]
```

Install:
```bash
pip install pre-commit --break-system-packages
pre-commit install
pre-commit run --all-files  # One-time run on existing code
```

---

## CI Pipeline Snippet

Generic — adapt to your CI system:

```bash
#!/usr/bin/env bash
# ci/lint-bash.sh — run in CI before any other steps
set -euo pipefail

SCRIPTS=$(find . -name '*.sh' -not -path '*/vendor/*' -not -path '*/.git/*')

echo "==> Syntax check (bash -n)"
echo "${SCRIPTS}" | xargs -I{} bash -n {}

echo "==> ShellCheck"
echo "${SCRIPTS}" | xargs shellcheck --shell=bash

echo "==> shfmt (formatting)"
echo "${SCRIPTS}" | xargs shfmt -i 2 -ci -bn -d

echo "==> All checks passed"
```

For GitHub Actions:
```yaml
- name: Lint shell scripts
  run: |
    find . -name '*.sh' | xargs shellcheck --shell=bash
    find . -name '*.sh' | xargs shfmt -i 2 -ci -bn -d
```

---

## Quick Install Cheatsheet

```bash
# macOS — everything in one shot
brew install shellcheck shfmt bats-core

# Debian/Ubuntu
apt-get install -y shellcheck
go install mvdan.cc/sh/v3/cmd/shfmt@latest
npm install -g bats  # or via apt: apt-get install bats

# Alpine (CI containers)
apk add shellcheck bash
go install mvdan.cc/sh/v3/cmd/shfmt@latest
```

Verify:
```bash
shellcheck --version
shfmt --version
bats --version
```
