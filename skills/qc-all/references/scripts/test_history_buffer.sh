#!/usr/bin/env bash
set -euo pipefail

SCRIPT="$(cd "$(dirname "$0")" && pwd)/append_history.py"
TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

assert_line_count() {
    local expected="$1"
    local actual
    actual="$(wc -l < "$TMPDIR/.qc-history.jsonl" | tr -d ' ')"
    if [ "$actual" != "$expected" ]; then
        echo "FAIL: expected $expected lines, got $actual" >&2
        exit 1
    fi
}

for i in $(seq 1 25); do
    RUN_ID="$(printf "2026-05-17T00:00:%02dZ-%07d" "$i" "$i")"
    printf '{"schema_version":"1.0","skill":"qc-all","run_id":"%s","git_sha":"abc1234","findings":[],"verdict":"READY"}\n' \
        "$RUN_ID" > "$TMPDIR/r${i}.json"
    python3 "$SCRIPT" "$TMPDIR/r${i}.json" --history-path "$TMPDIR/.qc-history.jsonl"
    if [ "$i" -eq 21 ]; then
        assert_line_count 20
    fi
done

assert_line_count 20

FIRST_RUN_ID="$(python3 -c "import json,sys; print(json.loads(sys.stdin.readline())['run_id'])" < "$TMPDIR/.qc-history.jsonl")"
EXPECTED_RUN_ID="$(printf "2026-05-17T00:00:%02dZ-%07d" 6 6)"
if [ "$FIRST_RUN_ID" != "$EXPECTED_RUN_ID" ]; then
    echo "FAIL: first run_id is '$FIRST_RUN_ID', expected '$EXPECTED_RUN_ID'" >&2
    exit 1
fi

echo "PASS: all assertions passed"
