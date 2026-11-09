#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# Script: run_tests.sh
# Description: Offline tests for fetch_ticket_context.sh against a stubbed
#   acli-pii. Asserts on rendering, exit codes, and that only acli-pii is used
#   without any PII-bypass flag. Does not touch Jira.
# Usage: tests/run_tests.sh
# Dependencies: jq
# -----------------------------------------------------------------------------
set -uo pipefail

TESTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly TESTS_DIR
readonly SCRIPT="${TESTS_DIR}/../scripts/fetch_ticket_context.sh"
readonly FIXTURES="${TESTS_DIR}/fixtures"

WORK_DIR="$(mktemp -d)"
readonly WORK_DIR
trap 'rm -rf "${WORK_DIR}"' EXIT
readonly STUB_DIR="${WORK_DIR}/bin"
readonly STUB_LOG="${WORK_DIR}/calls.log"

FAILURES=0
OUT="" ERR="" RC=0

install_stubs() {
  mkdir -p "${STUB_DIR}"
  cat >"${STUB_DIR}/acli-pii" <<'EOF'
#!/usr/bin/env bash
echo "acli-pii $*" >> "${STUB_LOG}"
if [[ "$3" == "view" ]]; then
  key=$4
  if [[ "${key}" == "CLIN-500" ]]; then echo "boom" >&2; exit 1; fi
  if [[ "${key}" == "CLIN-414" ]]; then head -c 2000 /dev/zero | tr '\0' 'x' >&2; exit 1; fi
  [[ -f "${FIXTURES}/view-${key}.json" ]] || { echo "Issue does not exist: ${key}" >&2; exit 1; }
  cat "${FIXTURES}/view-${key}.json"
elif [[ "$3" == "comment" ]]; then
  key=$6
  if [[ -f "${FIXTURES}/comments-${key}.json" ]]; then cat "${FIXTURES}/comments-${key}.json"; else echo "[]"; fi
fi
EOF
  cat >"${STUB_DIR}/acli" <<'EOF'
#!/usr/bin/env bash
echo "PLAIN acli $*" >> "${STUB_LOG}"
exit 1
EOF
  chmod +x "${STUB_DIR}/acli-pii" "${STUB_DIR}/acli"
}

run() {
  : >"${STUB_LOG}"
  RC=0
  # env, not an inline assignment: STUB_LOG and FIXTURES are readonly here.
  OUT="$(env PATH="${STUB_DIR}:${PATH}" STUB_LOG="${STUB_LOG}" FIXTURES="${FIXTURES}" \
    "${SCRIPT}" "$@" 2>"${WORK_DIR}/stderr")" || RC=$?
  ERR="$(<"${WORK_DIR}/stderr")"
}

fail() {
  echo "FAIL: $1"
  FAILURES=$((FAILURES + 1))
}

assert_rc() { [[ "${RC}" == "$2" ]] || fail "$1: exit ${RC}, expected $2 (stderr: ${ERR})"; }
assert_has() { [[ "${OUT}" == *"$2"* ]] || fail "$1: output missing '$2'"; }
assert_lacks() { [[ "${OUT}" != *"$2"* ]] || fail "$1: output unexpectedly has '$2'"; }
assert_calls_lack() { ! grep -qE "$2" "${STUB_LOG}" || fail "$1: calls matched /$2/"; }

test_ticket_with_epic() {
  run CLIN-1
  assert_rc epic 0
  assert_has epic "# JIRA Ticket: CLIN-1"
  assert_has epic "- Summary: Story under epic"
  assert_has epic "- Summary: The epic"
  assert_has epic "- Assignee: Jane Doe"
  assert_has epic "- Labels: TeamICO.Demoable, backend"
  assert_has epic "- Components: dokSystem"
  assert_has epic "- Fix Versions: Sprint 342"
  assert_has epic "- Story Points: 5"
  assert_has epic "- Linked Issues: blocks CLIN-50, is blocked by CLIN-51"
  assert_has epic $'Why we need this.\n- first\n- second\nspec (https://example.invalid/spec)'
  assert_has epic "### Alice Example — 2026-01-02T10:00:00.000+0000"
  assert_has epic "Root cause is the operator."
  assert_has epic "Plain string comment."
  assert_has epic "## Parent Epic Metadata"
  assert_has epic "- Assignee: N/A"
  assert_has epic "Plain-string epic description under CLIN-100."
  assert_lacks epic $'\n\n\n## References'
  assert_has epic "### Carol Epic — 2026-02-01T09:00:00.000+0000"
  [[ "${OUT}" == *"## Ticket Metadata"*"## Ticket Description"*"## Ticket Comments"*"## Parent Epic Metadata"*"## Parent Epic Description"*"## Parent Epic Comments"*"## References"* ]] \
    || fail "epic: sections out of order"
}

test_references() {
  run CLIN-1
  assert_rc references 0
  assert_has references $'### Links\n- https://example.invalid/spec (CLIN-1)'
  assert_has references "- CLIN-77 (CLIN-1)"
  assert_has references "- CLIN-88 (CLIN-9)"
  assert_has references "- CLIN-100 (CLIN-9)"
  assert_has references "- charts/app/values.yaml (CLIN-1)"
  assert_has references "- \`tms-operator\` (CLIN-1)"
  assert_has references "- spec.md (id 1455347) (CLIN-1)"
  assert_lacks references "- UTF-8"
  assert_lacks references "- CLIN-50"
  assert_lacks references "- CLIN-9 ("
  assert_lacks references "https://example.invalid/spec)"$'\n- https://example.invalid/spec'
  run CLIN-2
  assert_has references-empty $'## References\n'
  assert_has references-empty "No references found."
}

test_no_parent() {
  run CLIN-2
  assert_rc no-parent 0
  assert_has no-parent "No description provided."
  assert_has no-parent "No comments."
  assert_has no-parent "- Story Points: N/A"
  assert_has no-parent $'## Parent Epic Metadata\nNo parent epic found.'
  assert_lacks no-parent "Parent Epic Description"
}

test_non_epic_parent() {
  run CLIN-3
  assert_rc non-epic-parent 0
  assert_has non-epic-parent "No parent epic found."
  assert_lacks non-epic-parent "Parent Epic Comments"
}

test_error_exit_codes() {
  run CLIN-404
  assert_rc not-found 3
  run CLIN-500
  assert_rc acli-failure 6
  run CLIN-6
  assert_rc bad-shape 5
  run CLIN-414
  assert_rc proxy-error 6
  ((${#ERR} < 700)) || fail "proxy-error: stderr not truncated (${#ERR} chars)"
}

test_incomplete_comment_page_is_flagged() {
  run CLIN-7
  assert_rc comment-page 0
  assert_has comment-page "Only the first page."
  assert_has comment-page "NOTE: 149 more comment(s) exist than were returned"
  run CLIN-1
  assert_lacks comment-page-complete "NOTE: "
}

test_invalid_keys_never_reach_acli() {
  local bad
  for bad in "clin-1" "CLIN" "https://example.invalid/browse/CLIN-1" ""; do
    run "${bad}"
    assert_rc "invalid '${bad}'" 2
    [[ ! -s "${STUB_LOG}" ]] || fail "invalid '${bad}': acli-pii was called"
  done
}

test_fails_closed_without_acli_pii() {
  RC=0
  OUT="$(env PATH="/usr/bin:/bin" "${SCRIPT}" CLIN-1 2>"${WORK_DIR}/stderr")" || RC=$?
  ERR="$(<"${WORK_DIR}/stderr")"
  assert_rc no-acli-pii 4
  [[ "${ERR}" == *"refusing to fall back"* ]] || fail "no-acli-pii: missing refusal message"
}

test_only_acli_pii_without_bypass_flags() {
  run CLIN-1
  assert_calls_lack safety '^PLAIN acli'
  assert_calls_lack safety 'pii-skip|disable-pii|pii-only|allow-masked-write'
  assert_calls_lack safety 'workitem (edit|create|transition|assign|delete|move|link|attachment)'
  assert_calls_lack safety '\*all'
  grep -q -- '--fields key,summary,.*Story Points' "${STUB_LOG}" || fail "safety: explicit field list not requested"
  grep -q -- '--limit 1000' "${STUB_LOG}" || fail "safety: comment list not called with --limit 1000"
  ! grep -qE 'pii-skip|disable-pii' "${SCRIPT}" || fail "safety: script mentions a PII bypass flag"
}

test_output_file() {
  local target="${WORK_DIR}/out.md"
  run CLIN-2
  local stdout_doc="${OUT}"
  run -o "${target}" CLIN-2
  assert_rc output-file 0
  [[ "${OUT}" == "${target}" ]] || fail "output-file: expected path on stdout, got '${OUT}'"
  [[ "$(<"${target}")" == "${stdout_doc}" ]] || fail "output-file: content differs from stdout"
}

main() {
  install_stubs
  test_ticket_with_epic
  test_references
  test_no_parent
  test_non_epic_parent
  test_error_exit_codes
  test_incomplete_comment_page_is_flagged
  test_invalid_keys_never_reach_acli
  test_fails_closed_without_acli_pii
  test_only_acli_pii_without_bypass_flags
  test_output_file
  if ((FAILURES > 0)); then
    echo "${FAILURES} failure(s)"
    exit 1
  fi
  echo "all tests passed"
}

main "$@"
