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
#   4. The budgets / budgets_hr_expense suites pass ONLY with no client bridge
#      installed -- both bridges add a *required* anchor field to
#      operations.budget.line, so a bare line cannot be created once either is
#      present. Each suite therefore needs its own database.
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

ADDONS="$ODOO_PATH/addons,$REPO/shared,$REPO/commodity_trading,$REPO/omnifreight"
failures=0

# run <label> <install> <test-tags|""> <expect-installed> [forbid-installed]
#
# `forbid` is the load-bearing half for the shared/ invariants: asserting that the
# module installed proves nothing, because it installs fine while dragging the
# whole freight stack behind it. The claim is about what must NOT come along.
run() {
  local label=$1 install=$2 tags=$3 expect=$4 forbid=${5:-}
  local db="verify_$label"

  dropdb --if-exists "$db" >/dev/null 2>&1
  createdb "$db" >/dev/null 2>&1

  local args=(-d "$db" --addons-path="$ADDONS" -i "$install"
              --stop-after-init --http-port="$HTTP_PORT")
  if [ -n "$tags" ]; then
    args+=(--test-enable --test-tags="$tags" --log-level=test)
  else
    args+=(--log-level=warn)
  fi

  local out
  out=$("$PYTHON" "$ODOO_BIN" "${args[@]}" 2>&1)

  local bad ok result
  bad=$(printf '%s' "$out" | grep -cE "CRITICAL|ParseError|Failed to (load|initialize)")
  result=$(printf '%s' "$out" | grep -E "tests\.result" | tail -1)
  ok=$(psql -d "$db" -tAc \
    "select count(*) from ir_module_module where state='installed' and name in ($expect)" 2>/dev/null)

  # Count of expected modules = comma-separated field count (wc -l would report 0
  # for a single entry, since there is no trailing newline).
  local want
  want=$(printf '%s' "$expect" | awk -F',' '{print NF}')

  local leaked=""
  if [ -n "$forbid" ]; then
    leaked=$(psql -d "$db" -tAc \
      "select string_agg(name, ', ') from ir_module_module where state='installed' and name in ($forbid)" 2>/dev/null)
  fi

  if [ "$bad" -gt 0 ] || [ "${ok:-0}" != "$want" ] || [ -n "$leaked" ] \
     || printf '%s' "$result" | grep -q "[1-9][0-9]* \(failed\|error\)"; then
    printf '  FAIL  %-24s (installed %s/%s)\n' "$label" "${ok:-0}" "$want"
    [ -n "$leaked" ] && printf '        must not have been installed: %s\n' "$leaked"
    printf '%s' "$out" | grep -E "CRITICAL|ParseError|FAIL:|ERROR:" | head -4 | sed 's/^/        /'
    failures=$((failures + 1))
  else
    printf '  ok    %-24s %s\n' "$label" "${result##*result: }"
  fi

  dropdb --if-exists "$db" >/dev/null 2>&1
}

VERTICALS="'omni_ops','omni_budget','quotation','trading','trading_budget','mrp'"

echo "Invariant 1: shared/ modules install with no vertical present"
run budgets_alone      budgets             /budgets            "'budgets'"            "$VERTICALS"
run bhe_alone          budgets_hr_expense  /budgets_hr_expense "'budgets_hr_expense'" "$VERTICALS"
run bank_alone         ele_bank_reconcile /ele_bank_reconcile "'ele_bank_reconcile'" "$VERTICALS"
run ap_alone           ele_ap_validation  ""                  "'ele_ap_validation'" "$VERTICALS"

echo "Invariant 2: omni_ops installs without budgeting"
run omni_ops_alone     omni_ops            /omni_ops           "'omni_ops'" \
                       "'budgets','budgets_hr_expense','omni_budget'"
run omni_budget_ontop  omni_budget         ""                  "'omni_ops','omni_budget','budgets','budgets_hr_expense'"

echo "Invariant 3: full stacks and both verticals together"
run freight_stack      omni_ops,omni_budget,ele_ap_validation,ele_bank_reconcile "" \
                       "'omni_ops','omni_budget','ele_ap_validation','ele_bank_reconcile'"
run trading_budget     trading_budget      /trading_budget     "'trading','trading_budget','budgets','budgets_hr_expense'"
run both_verticals     trading_budget,omni_budget ""           "'trading_budget','omni_budget','omni_ops','trading'"

echo
if [ "$failures" -gt 0 ]; then
  echo "$failures scenario(s) FAILED"
  exit 1
fi
echo "all scenarios passed"
