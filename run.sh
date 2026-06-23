#!/usr/bin/env bash
# Reproducible end-to-end AxonOS intent-flow demo.
#   ./run.sh            build fixtures + expected outputs + SHA256SUMS
#   ./run.sh --verify   regenerate everything and prove it matches (CI gate)
set -euo pipefail
cd "$(dirname "$0")"
HASHED="fixtures/synthetic_trace.csv fixtures/consent_events.csv \
expected/intent_observations.jsonl expected/intent_observations.hex \
expected/decisions.jsonl expected/summary.json"

case "${1:-build}" in
  --verify|verify)
    tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
    python3 scripts/gen_fixture.py "$tmp/fixtures" >/dev/null
    PYTHONPATH=src python3 -m axonos_e2e.runner "$tmp/fixtures" "$tmp/expected" >/dev/null
    fail=0
    for f in $HASHED; do
      if ! diff -q "$f" "$tmp/$f" >/dev/null 2>&1; then echo "MISMATCH (regeneration): $f"; fail=1; fi
    done
    if ! sha256sum -c SHA256SUMS >/dev/null 2>&1; then echo "MISMATCH (SHA256SUMS)"; fail=1; fi
    if [ "$fail" -eq 0 ]; then
      echo "OK: end-to-end output reproduced bit-for-bit; all SHA-256 hashes verified."
    else
      echo "FAIL: the demo did not reproduce deterministically."; exit 1
    fi
    ;;
  *)
    python3 scripts/gen_fixture.py fixtures
    PYTHONPATH=src python3 -m axonos_e2e.runner fixtures expected >/dev/null
    sha256sum $HASHED > SHA256SUMS
    echo "built: fixtures/, expected/, SHA256SUMS"
    echo "sample app:  python3 examples/cursor_app.py"
    ;;
esac
