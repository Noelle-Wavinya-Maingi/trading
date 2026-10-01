#!/usr/bin/env bash
#
# Verifies the architectural invariants of this repository against a real Odoo
# instance. These are claims the layout makes, not just style preferences:
#
#   1. Anything in shared/ installs with NO vertical module present.
#      This is what makes those modules reusable by another client at all.
#   2. omni_ops installs with no budgeting present (the dependency inversion
#      that makes omni_budget genuinely optional).
#   3. The two verticals coexist in one database (they collided until their
#      budget-line anchor fields were namespaced).
#   4. Shared budget suites use their own databases, without client extensions
#      changing the model behavior or test fixtures.
#   5. Each vertical's order.bridge.mixin/operations.budget.line hooks still
#      run correctly when another vertical's hooks are ALSO registered on the
#      same host model. This collided twice in practice: confirming a freight
#      quotation could silently try to create a trading.trade instead of a
#      freight file (and vice versa), and a trading budget line could look
#      anchor-less because omni_budget's anchor logic ran instead of its own.
#      Both were fixed by registering hooks into an accumulating list instead
#      of overriding a single method slot -- this scenario actually runs both
#      verticals' own test suites together (not just checking they install),
#      so a future collision of this shape fails here, not in production.
#
# Every scenario gets a throwaway database, created and dropped here.
#
# Usage:
#   ODOO_PATH=/path/to/odoo tools/verify_boundaries.sh
#
set -uo pipefail

ODOO_PATH="${ODOO_PATH:-$HOME/Documents/odoo}"
ODOO_BIN="$ODOO_PATH/odoo-bin"
PYTHON="${ODOO_PYTHON:-$ODOO_PATH/venv/bin/python}"
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HTTP_PORT="${HTTP_PORT:-8169}"

# `[ -x "$PYTHON" ]` only tests a literal path -- it does not do a $PATH
# lookup, so ODOO_PYTHON=python (a bare command name, as used in CI where
# there's no venv) would fail this check even though `python` resolves fine.
# `command -v` handles both a bare command and an explicit path.
PYTHON="$(command -v "$PYTHON" 2>/dev/null || true)"

if [ -z "$PYTHON" ] || [ ! -f "$ODOO_BIN" ]; then
  echo "error: Odoo not found. Set ODOO_PATH (currently '$ODOO_PATH') and/or ODOO_PYTHON." >&2
  exit 2
fi

# Discover addon roots from manifests so new product folders work in CI.
CUSTOM_ROOTS=$("$PYTHON" "$REPO/tools/ci_scope.py" --addon-roots) || exit 2
ADDONS="$ODOO_PATH/odoo/addons,$ODOO_PATH/addons,$CUSTOM_ROOTS"
if [ -n "${ODOO_ENTERPRISE_PATH:-}" ]; then
  ADDONS="$ODOO_ENTERPRISE_PATH,$ADDONS"
fi
failures=0

# CI supplies an explicit module list. Without it, run the full suite locally.
# Generate the plan first so planner errors cannot silently skip verification.
plan_args=(--rows community)
if [ -n "${ODOO_ENTERPRISE_PATH:-}" ]; then
  plan_args=(--rows enterprise)
fi
if [ "${VERIFY_MODULES+x}" = x ]; then
  plan_args+=(--modules "$VERIFY_MODULES")
fi
plan=$("$PYTHON" "$REPO/tools/ci_scope.py" "${plan_args[@]}") || exit 2
if [ -z "$plan" ]; then
  echo "No affected addons for this edition."
  exit 0
fi

# run <label> <install> <test-tags|""> <expect-installed> [forbid-installed]
#
# `forbid` is the load-bearing half for the shared/ invariants: asserting that the
# module installed proves nothing, because it installs fine while dragging the
# whole freight stack behind it. The claim is about what must NOT come along.
run() {
  local label=$1 install=$2 tags=$3 expect=$4 forbid=${5:-}
  local db="verify_${label}_$$"

  if ! createdb "$db"; then
    echo "FAIL: could not create $db" >&2
    failures=$((failures + 1))
    return
  fi

  local args=(-d "$db" --addons-path="$ADDONS" -i "$install"
              --stop-after-init --http-port="$HTTP_PORT")
  if [ -n "$tags" ]; then
    args+=(--test-enable --test-tags="$tags" --log-level=test)
  else
    args+=(--log-level=warn)
  fi

  local out status
  out=$("$PYTHON" "$ODOO_BIN" "${args[@]}" 2>&1)
  status=$?

  local bad ok result query_status
  bad=$(printf '%s' "$out" | grep -cE "CRITICAL|ParseError|Failed to (load|initialize)")
  result=$(printf '%s' "$out" | grep -E "tests\.result" | tail -1)
  ok=$(psql -d "$db" -tAc \
    "select count(*) from ir_module_module where state='installed' and name in ($expect)" 2>/dev/null)
  query_status=$?

  # Count of expected modules = comma-separated field count (wc -l would report 0
  # for a single entry, since there is no trailing newline).
  local want
  want=$(printf '%s' "$expect" | awk -F',' '{print NF}')

  local leaked=""
  if [ -n "$forbid" ]; then
    leaked=$(psql -d "$db" -tAc \
      "select string_agg(name, ', ') from ir_module_module where state='installed' and name in ($forbid)" 2>/dev/null)
    [ "$?" -eq 0 ] || query_status=1
  fi

  if [ "$status" -ne 0 ] || [ "$query_status" -ne 0 ] || [ "$bad" -gt 0 ] || { [ -n "$tags" ] && [ -z "$result" ]; } || [ "${ok:-0}" != "$want" ] || [ -n "$leaked" ] \
     || printf '%s' "$result" | grep -q "[1-9][0-9]* \(failed\|error\)"; then
    printf '  FAIL  %-24s (installed %s/%s)\n' "$label" "${ok:-0}" "$want"
    printf '        Odoo exit: %s; SQL check exit: %s\n' "$status" "$query_status"
    [ -n "$leaked" ] && printf '        must not have been installed: %s\n' "$leaked"
    printf '%s' "$out" | grep -E "CRITICAL|ParseError|FAIL:|ERROR:|ERROR |Traceback" | head -12 | sed 's/^/        /'
    failures=$((failures + 1))
  else
    printf '  ok    %-24s %s\n' "$label" "${result##*result: }"
  fi

  dropdb --if-exists "$db" >/dev/null 2>&1
}

echo "Selected checks:"
while IFS='|' read -r label install tags expect forbid; do
  [ -n "$label" ] || continue
  [ "$forbid" = '-' ] && forbid=""
  printf '  %s: install [%s], tests [%s]\n' "$label" "$install" "$tags"
  run "$label" "$install" "$tags" "$expect" "$forbid"
done <<< "$plan"

echo
if [ "$failures" -gt 0 ]; then
  echo "$failures scenario(s) FAILED"
  exit 1
fi
echo "all scenarios passed"
