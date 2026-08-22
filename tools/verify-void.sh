#!/usr/bin/env bash
set -euo pipefail
# 2026 battle-tested verifier -- void-nexus. Returns 0 only if agent truly finished.
RUN_ID="${RUN_ID:-}"
RELAY=".opencode-relay.md"
FAIL=0
echo "----- VERIFICATION REPORT -----"
if [[ -f "$RELAY" ]]; then
  dep_rows=$(grep -c "deps-verified\|deps-fixed" "$RELAY" 2>/dev/null || echo 0)
  echo "Dependency table rows: $dep_rows (need >=19, need 19 rows deps-verified/deps-fixed)"
  if [[ "$dep_rows" -lt 19 ]]; then
    echo "FAIL: dependency audit table has $dep_rows rows, need 19"
    FAIL=1
  else
    echo "PASS: Dependency table: $dep_rows rows"
  fi
  for tool in "xlint" "xbps-install" "xbps-src"; do
    if ! grep -qi "$tool.*PASS\|PASS.*$tool" "$RELAY"; then
    echo "FAIL: NOT COMPLETE -- relay missing fresh evidence for $tool (with PASS result)"
    FAIL=1
  fi
  done
  if ! grep -qi "install-test table\|xbps install test" "$RELAY"; then
    echo "FAIL: install-test table missing in relay"
    FAIL=1
  else
    echo "PASS: Install-test table present"
  fi
  if ! grep -qi "DOCKER BATTLE TEST\|void-glibc-full\|ldd" "$RELAY"; then
    echo "FAIL: NOT COMPLETE -- relay missing Docker battle test evidence"
    FAIL=1
  fi
else
  echo "FAIL: $RELAY missing"
  FAIL=1
fi
bad=0
for tmpl in srcpkgs/*/template; do
  [[ -f "$tmpl" ]] || continue
  if ! grep -q "^pkgname=" "$tmpl" 2>/dev/null; then echo "FAIL: $tmpl missing pkgname"; bad=$((bad+1)); fi
done
if [[ "$bad" -gt 0 ]]; then echo "FAIL: $bad templates malformed"; FAIL=1; fi
if [[ "$FAIL" -ne 0 ]]; then echo "FAIL: NOT COMPLETE -- agent must continue working"; exit 1; fi
echo "PASS: VERIFICATION PASSED -- all 19 deps rows, evidence, install+battle test present"
exit 0
