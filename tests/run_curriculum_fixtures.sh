#!/usr/bin/env bash
# Run verify.py checks 1-8 for each curriculum self-test/guard against the
# State its fixture request defines. Fails if any run fails.
set -euo pipefail
PY=${PYTHON:-python3}
grep -v '^#' tests/curriculum_fixture_cases.txt | while read -r req ids; do
  [ -z "$req" ] && continue
  echo "=== $req ($ids)"
  "$PY" tools/verify.py --request "$req" --ids "$ids" \
      problems/curriculum-selftests.json problems/false-rejection-guards.json
done
