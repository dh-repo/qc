#!/usr/bin/env bash
set -euo pipefail

SCRIPT_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/$(basename "${BASH_SOURCE[0]}")"
SCRIPT_DIR="$(dirname "$SCRIPT_PATH")"
FIXTURES_DIR="${SCRIPT_DIR}/../fixtures"

TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
GIT_SHA=$(git rev-parse --short=7 HEAD 2>/dev/null || echo "0000000")
RUN_ID="${TIMESTAMP}-${GIT_SHA}"
FINDINGS_DIR=".qc-findings"
OUTPUT="${FINDINGS_DIR}/qc-deterministic.json"
QC_COVERAGE_THRESHOLD="${QC_COVERAGE_THRESHOLD:-80}"

FINDINGS_ARRAY='[]'
RUFF_IDX=0; MYPY_IDX=0; COV_IDX=0; VULT_IDX=0; AUDIT_IDX=0; TEST_IDX=0; MISS_IDX=0
MISSING_TOOL=0

usage() {
  cat <<'USAGE'
Usage: qc_deterministic.sh [OPTIONS]

CI gate for Python projects. Runs ruff, mypy --strict, coverage, vulture,
pip-audit, and the project test suite. Emits .qc-findings/qc-deterministic.json
matching the qc-finding schema.

Options:
  --help           Show this help message
  --self-test      Run against fixture projects to verify script correctness
  --inject NAME    With --self-test: inject an error scenario
                   Names: ruff-error, mypy-error, test-fail, missing-tool

Environment:
  QC_COVERAGE_THRESHOLD  Minimum coverage % (default: 80)
  QC_TEST_RUNNER         Override test runner module (e.g. pytest)
  QC_SKIP_PIPAUDIT       If "1", skip pip-audit (env-level CVEs are not
                         a project-level finding; useful for self-test
                         and for CI envs that audit pip separately)

Exit codes:
  0  READY or READY_WITH_DEBT
  1  NOT_READY (P0 or open P1 findings present)
  2  Missing required tool (also emits a P0 finding)
USAGE
}

# Detect a tool: checks PATH first, then python3 -m fallback.
# Args: <cmd-name> [<python-module-name>]
# Prints the invocation string on success, returns 1 on failure.
detect_tool() {
  local name="$1"
  local module="${2:-}"
  if command -v "$name" &>/dev/null; then
    printf '%s' "$(command -v "$name")"
    return 0
  fi
  if [[ -n "$module" ]] && python3 -c \
    "import importlib.util; exit(0 if importlib.util.find_spec('${module}') is not None else 1)" \
    2>/dev/null; then
    printf '%s' "python3 -m ${module}"
    return 0
  fi
  return 1
}

emit_finding() {
  local id="$1" severity="$2" file="$3" what="$4"
  local item
  item=$(jq -n \
    --arg id "$id" --arg severity "$severity" \
    --arg file "$file" --arg what "$what" \
    '{id:$id,severity:$severity,file:$file,what:$what,fixed:false}')
  FINDINGS_ARRAY=$(printf '%s' "$FINDINGS_ARRAY" | jq ". + [$item]")
}

compute_verdict() {
  local p0 open_p1 total
  p0=$(printf '%s' "$FINDINGS_ARRAY" | jq '[.[]|select(.severity=="P0")]|length')
  open_p1=$(printf '%s' "$FINDINGS_ARRAY" | jq \
    '[.[]|select(.severity=="P1" and .fixed==false and ((.deferred_because//"")==""))]|length')
  if [[ "$p0" -gt 0 ]] || [[ "$open_p1" -gt 0 ]]; then
    printf 'NOT_READY'; return
  fi
  total=$(printf '%s' "$FINDINGS_ARRAY" | jq 'length')
  if [[ "$total" -gt 0 ]]; then
    printf 'READY_WITH_DEBT'; return
  fi
  printf 'READY'
}

finalize_json() {
  local verdict
  verdict=$(compute_verdict)
  mkdir -p "$FINDINGS_DIR"
  jq -n \
    --arg schema_version "1.0" \
    --arg skill "qc-deterministic" \
    --arg run_id "$RUN_ID" \
    --arg git_sha "$GIT_SHA" \
    --argjson findings "$FINDINGS_ARRAY" \
    --arg verdict "$verdict" \
    '{schema_version:$schema_version,skill:$skill,run_id:$run_id,
      git_sha:$git_sha,findings:$findings,verdict:$verdict}' \
    > "$OUTPUT"
  printf 'Verdict: %s  →  %s\n' "$verdict" "$OUTPUT" >&2
}

check_ruff() {
  local cmd
  if ! cmd=$(detect_tool ruff ruff 2>/dev/null); then
    MISS_IDX=$((MISS_IDX+1))
    emit_finding "DMISSING${MISS_IDX}" "P0" "" "tool not installed: ruff"
    MISSING_TOOL=1; return
  fi
  local out="" rc=0
  out=$($cmd check . --output-format json 2>/dev/null) || rc=$?
  [[ "$rc" -eq 0 ]] && return
  while IFS= read -r item; do
    [[ -z "$item" ]] && continue
    RUFF_IDX=$((RUFF_IDX+1))
    local f code msg
    f=$(printf '%s' "$item"   | jq -r '.filename//"unknown"')
    code=$(printf '%s' "$item" | jq -r '.code//"E"')
    msg=$(printf '%s' "$item"  | jq -r '.message//"ruff violation"')
    emit_finding "DRUFF${RUFF_IDX}" "P2" "$f" "${code}: ${msg}"
  done < <(printf '%s' "$out" | jq -c '.[]' 2>/dev/null || true)
}

check_mypy() {
  local cmd
  if ! cmd=$(detect_tool mypy mypy 2>/dev/null); then
    MISS_IDX=$((MISS_IDX+1))
    emit_finding "DMISSING${MISS_IDX}" "P0" "" "tool not installed: mypy"
    MISSING_TOOL=1; return
  fi
  local out="" rc=0
  out=$($cmd . --strict --output=json 2>/dev/null) || rc=$?
  [[ "$rc" -eq 0 ]] && return
  while IFS= read -r line; do
    [[ -z "$line" ]] && continue
    local sev
    sev=$(printf '%s' "$line" | jq -r '.severity//"note"' 2>/dev/null || echo "note")
    [[ "$sev" != "error" ]] && continue
    MYPY_IDX=$((MYPY_IDX+1))
    local f msg
    f=$(printf '%s' "$line" | jq -r '.file//"unknown"'     2>/dev/null || echo "unknown")
    msg=$(printf '%s' "$line" | jq -r '.message//"mypy error"' 2>/dev/null || echo "mypy error")
    emit_finding "DMYPY${MYPY_IDX}" "P1" "$f" "$msg"
  done < <(printf '%s\n' "$out")
}

# Returns the pytest or unittest module invocation (without python3 -m prefix).
_detect_test_module() {
  if [[ -n "${QC_TEST_RUNNER:-}" ]]; then
    printf '%s' "$QC_TEST_RUNNER"; return
  fi
  if grep -qE '\[tool\.pytest' pyproject.toml 2>/dev/null || [[ -f conftest.py ]]; then
    if python3 -c "import pytest" 2>/dev/null || command -v pytest &>/dev/null; then
      printf 'pytest'; return
    fi
  fi
  printf 'unittest'
}

check_tests() {
  local cov_cmd
  if ! cov_cmd=$(detect_tool coverage coverage 2>/dev/null); then
    MISS_IDX=$((MISS_IDX+1))
    emit_finding "DMISSING${MISS_IDX}" "P0" "" "tool not installed: coverage"
    MISSING_TOOL=1; return
  fi

  local runner
  runner=$(_detect_test_module)
  local runner_args="-v --tb=short"
  [[ "$runner" == "unittest" ]] && runner_args="discover -s tests"

  $cov_cmd erase 2>/dev/null || true

  local out="" rc=0
  # shellcheck disable=SC2086
  out=$($cov_cmd run -m $runner $runner_args 2>&1) || rc=$?

  if [[ "$rc" -ne 0 ]]; then
    local found=0
    while IFS= read -r line; do
      if [[ "$line" =~ ^FAILED[[:space:]] ]]; then
        TEST_IDX=$((TEST_IDX+1))
        local tname="${line#FAILED }"
        tname="${tname%% -*}"
        emit_finding "DTEST${TEST_IDX}" "P0" "$tname" "test failed: $tname"
        found=1
      elif [[ "$line" =~ ^FAIL:[[:space:]](.+) ]]; then
        TEST_IDX=$((TEST_IDX+1))
        emit_finding "DTEST${TEST_IDX}" "P0" "${BASH_REMATCH[1]}" \
          "test failed: ${BASH_REMATCH[1]}"
        found=1
      fi
    done < <(printf '%s\n' "$out")
    if [[ "$found" -eq 0 ]]; then
      TEST_IDX=$((TEST_IDX+1))
      emit_finding "DTEST${TEST_IDX}" "P0" "" "test runner exited with code $rc"
    fi
  fi
}

check_coverage() {
  local cov_cmd
  cov_cmd=$(detect_tool coverage coverage 2>/dev/null) || return 0
  local report_out="" rc=0
  report_out=$($cov_cmd report --fail-under="$QC_COVERAGE_THRESHOLD" 2>&1) || rc=$?
  if [[ "$rc" -ne 0 ]]; then
    COV_IDX=$((COV_IDX+1))
    local pct
    pct=$(printf '%s\n' "$report_out" | tail -1 | awk '{print $NF}' | tr -d '%' || echo "?")
    emit_finding "DCOV${COV_IDX}" "P1" "" \
      "coverage ${pct}% is below threshold ${QC_COVERAGE_THRESHOLD}%"
  fi
}

check_vulture() {
  local cmd
  if ! cmd=$(detect_tool vulture vulture 2>/dev/null); then
    MISS_IDX=$((MISS_IDX+1))
    emit_finding "DMISSING${MISS_IDX}" "P0" "" "tool not installed: vulture"
    MISSING_TOOL=1; return
  fi
  local out="" rc=0
  out=$($cmd . 2>/dev/null) || rc=$?
  [[ "$rc" -eq 0 ]] && return
  while IFS= read -r line; do
    [[ -z "$line" ]] && continue
    VULT_IDX=$((VULT_IDX+1))
    local f rest
    f="${line%%:*}"
    rest="${line#*: }"
    emit_finding "DVULT${VULT_IDX}" "P3" "$f" "dead code: $rest"
  done < <(printf '%s\n' "$out")
}

check_pipaudit() {
  [[ "${QC_SKIP_PIPAUDIT:-0}" == "1" ]] && return
  local cmd
  if ! cmd=$(detect_tool pip-audit pip_audit 2>/dev/null); then
    MISS_IDX=$((MISS_IDX+1))
    emit_finding "DMISSING${MISS_IDX}" "P0" "" "tool not installed: pip-audit"
    MISSING_TOOL=1; return
  fi
  local out="" rc=0
  out=$($cmd --format json 2>/dev/null) || rc=$?
  [[ "$rc" -eq 0 ]] && return
  while IFS= read -r dep; do
    [[ -z "$dep" ]] && continue
    local name version
    name=$(printf '%s' "$dep"    | jq -r '.name//"unknown"'    2>/dev/null || continue)
    version=$(printf '%s' "$dep" | jq -r '.version//"unknown"' 2>/dev/null || echo "unknown")
    while IFS= read -r vuln; do
      [[ -z "$vuln" ]] && continue
      AUDIT_IDX=$((AUDIT_IDX+1))
      local vid desc sev
      vid=$(printf '%s' "$vuln"  | jq -r '.id//"unknown"'         2>/dev/null || echo "unknown")
      desc=$(printf '%s' "$vuln" | jq -r '.description//.id//.id' 2>/dev/null || echo "$vid")
      sev="P1"
      printf '%s' "$desc" | grep -qi "critical" && sev="P0"
      emit_finding "DPIPAUDIT${AUDIT_IDX}" "$sev" "" \
        "${name}@${version}: ${vid} - ${desc:0:120}"
    done < <(printf '%s' "$dep" | jq -c '.vulns[]' 2>/dev/null || true)
  done < <(printf '%s' "$out" | jq -c '.dependencies[]' 2>/dev/null || true)
}

run_checks() {
  if ! command -v jq &>/dev/null; then
    printf 'FATAL: jq is required but not installed\n' >&2
    exit 2
  fi
  check_ruff
  check_mypy
  check_tests
  check_coverage
  check_vulture
  check_pipaudit
  finalize_json
  if [[ "$MISSING_TOOL" -eq 1 ]]; then
    exit 2
  fi
  local verdict
  verdict=$(compute_verdict)
  [[ "$verdict" == "NOT_READY" ]] && exit 1
  exit 0
}

# ── Self-test helpers ────────────────────────────────────────────────────────

_st_assert_exit() {
  local label="$1" expected="$2" actual="$3"
  if [[ "$actual" -ne "$expected" ]]; then
    printf 'SELF-TEST FAIL [%s]: expected exit %d, got %d\n' \
      "$label" "$expected" "$actual" >&2
    exit 1
  fi
  printf 'SELF-TEST PASS [%s]: exit %d\n' "$label" "$actual" >&2
}

_st_assert_severity() {
  local label="$1" file="$2" severity="$3"
  local count=0
  count=$(jq "[.findings[]|select(.severity==\"$severity\")]|length" "$file" 2>/dev/null \
    || echo 0)
  if [[ "$count" -eq 0 ]]; then
    printf 'SELF-TEST FAIL [%s]: no %s findings in %s\n' "$label" "$severity" "$file" >&2
    jq '.findings' "$file" >&2 2>/dev/null || true
    exit 1
  fi
  printf 'SELF-TEST PASS [%s]: %d %s finding(s)\n' "$label" "$count" "$severity" >&2
}

# Build a PATH string prefixed with venv/bin; optionally exclude dirs containing ruff.
_build_test_path() {
  local venv_dir="$1"
  local mask_ruff="${2:-false}"
  local new_path=""
  local combined="${venv_dir}/bin:${PATH}"
  while IFS= read -r dir; do
    [[ -z "$dir" ]] && continue
    if [[ "$mask_ruff" == "true" ]] && [[ -x "${dir}/ruff" ]]; then
      continue
    fi
    new_path="${new_path}${new_path:+:}${dir}"
  done < <(printf '%s' "$combined" | tr ':' '\n')
  printf '%s' "$new_path"
}

run_self_test() {
  local inject="${1:-}"
  printf '=== QC Deterministic Self-Test (inject: %s) ===\n' "${inject:-none}" >&2

  # Self-test verifies script plumbing, not pip-audit's env-level findings
  # (which are non-deterministic across environments).
  export QC_SKIP_PIPAUDIT=1

  local VENV
  VENV=$(mktemp -d /tmp/qc-selftest-XXXXX)
  # shellcheck disable=SC2064
  trap "rm -rf '${VENV}'" EXIT INT TERM

  printf 'Building self-test venv...\n' >&2
  python3 -m venv "${VENV}"
  "${VENV}/bin/pip" install ruff mypy vulture pip-audit pytest coverage \
    --quiet --disable-pip-version-check 2>/dev/null

  case "$inject" in
    "missing-tool")
      local fixture="${FIXTURES_DIR}/planted-error-repo"
      local test_path actual_exit=0
      test_path=$(_build_test_path "$VENV" true)
      (
        export PATH="$test_path"
        cd "$fixture"
        bash "$SCRIPT_PATH"
      ) || actual_exit=$?
      _st_assert_exit "missing-tool:exit" 2 "$actual_exit"
      _st_assert_severity "missing-tool:P0" \
        "${fixture}/.qc-findings/qc-deterministic.json" "P0"
      ;;

    "ruff-error"|"mypy-error"|"test-fail")
      local fixture="${FIXTURES_DIR}/planted-error-repo"
      local disabled_file
      case "$inject" in
        ruff-error) disabled_file="app/with_ruff_error.py.disabled" ;;
        mypy-error) disabled_file="app/with_mypy_error.py.disabled" ;;
        test-fail)  disabled_file="tests/test_failing.py.disabled"  ;;
      esac
      local active="${fixture}/${disabled_file%.disabled}"
      cp "${fixture}/${disabled_file}" "$active"
      local test_path actual_exit=0
      test_path=$(_build_test_path "$VENV" false)
      (
        export PATH="$test_path"
        cd "$fixture"
        bash "$SCRIPT_PATH"
      ) || actual_exit=$?
      rm -f "$active"
      _st_assert_exit "${inject}:exit" 1 "$actual_exit"
      local expected_sev="P2"
      [[ "$inject" == "mypy-error" ]] && expected_sev="P1"
      [[ "$inject" == "test-fail"  ]] && expected_sev="P0"
      _st_assert_severity "${inject}:${expected_sev}" \
        "${fixture}/.qc-findings/qc-deterministic.json" "$expected_sev"
      ;;

    "")
      local fixture="${FIXTURES_DIR}/clean-repo"
      local test_path actual_exit=0
      test_path=$(_build_test_path "$VENV" false)
      (
        export PATH="$test_path"
        cd "$fixture"
        bash "$SCRIPT_PATH"
      ) || actual_exit=$?
      _st_assert_exit "clean:exit" 0 "$actual_exit"
      local out_file="${fixture}/.qc-findings/qc-deterministic.json"
      local verdict
      verdict=$(jq -r '.verdict' "$out_file" 2>/dev/null || echo "missing")
      if [[ "$verdict" != "READY" ]]; then
        printf 'SELF-TEST FAIL [clean:verdict]: expected READY, got %s\n' "$verdict" >&2
        jq '.' "$out_file" >&2 2>/dev/null || true
        exit 1
      fi
      printf 'SELF-TEST PASS [clean:verdict]: READY\n' >&2
      ;;

    *)
      printf 'Unknown inject value: %s\nValid: ruff-error, mypy-error, test-fail, missing-tool\n' \
        "$inject" >&2
      exit 1
      ;;
  esac

  printf '=== Self-Test Complete: PASS ===\n' >&2
}

# ── Entry point ──────────────────────────────────────────────────────────────

case "${1:-}" in
  --help|-h)
    usage; exit 0 ;;
  --self-test)
    shift
    _inject=""
    if [[ "${1:-}" == "--inject" ]]; then
      _inject="${2:?'--inject requires a value'}"
      shift 2
    fi
    run_self_test "$_inject"
    ;;
  *)
    run_checks ;;
esac
