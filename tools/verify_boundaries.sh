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

# ODOO_ENTERPRISE_PATH is optional: when set (e.g. by CI's enterprise job, or
# a local checkout of odoo/enterprise), its addons are prepended so Enterprise
# view overrides/extensions of the same models are exercised too, not just
# Community. Unset in a plain Community dev environment, this is a no-op.
ADDONS="$ODOO_PATH/addons,$REPO/shared,$REPO/product/commodity_trading,$REPO/product/ap_validation,$REPO/product/bank_reconciliation,$REPO/custom/omnifreight,$REPO/third_parties"
if [ -n "${ODOO_ENTERPRISE_PATH:-}" ]; then
  ADDONS="$ODOO_ENTERPRISE_PATH,$ADDONS"
fi
failures=0

# VERIFY_SCOPE=all (the default, e.g. for local/manual runs) runs every
# scenario. CI sets it to 'all' whenever shared/ or this script itself
# changed, since shared/'s claim is "safe for every consumer" and can't be
# scoped to one client -- otherwise CI leaves it unset and passes
# VERIFY_TRADING/VERIFY_OMNIFREIGHT so only scenario groups for verticals
# that actually changed in this diff run. Add a VERIFY_<CLIENT> variable
# here for each new client vertical.
run_trading=1
run_omnifreight=1
if [ "${VERIFY_SCOPE:-all}" != "all" ]; then
  run_trading=0
  run_omnifreight=0
  [ "${VERIFY_TRADING:-false}" = "true" ] && run_trading=1
  [ "${VERIFY_OMNIFREIGHT:-false}" = "true" ] && run_omnifreight=1
fi

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

VERTICALS="'omni_ops','omni_budget','quotation','ele_trading','ele_trading_budget','mrp'"

echo "Invariant 1: shared/ modules install with no vertical present"
run budgets_alone      budgets             /budgets            "'budgets'"            "$VERTICALS"
run bhe_alone          budgets_hr_expense  /budgets_hr_expense "'budgets_hr_expense'" "$VERTICALS"
run ap_alone           ele_ap_validation  ""                  "'ele_ap_validation'" "$VERTICALS"

# ele_bank_reconcile no longer makes this claim: it moved to product/ and now
# depends on account_accountant (Enterprise), by design -- Community ships no
# UI to reconcile a bank statement line at all, so there is no standalone
# claim left to test on a Community-only run. Only exercise it when Enterprise
# is actually on the addons path.
if [ -n "${ODOO_ENTERPRISE_PATH:-}" ]; then
  echo "Invariant 1b: ele_bank_reconcile installs with no vertical present (Enterprise only)"
  run bank_alone       ele_bank_reconcile /ele_bank_reconcile "'ele_bank_reconcile'" "$VERTICALS"
else
  echo "Invariant 1b: ele_bank_reconcile skipped (requires Enterprise, none on this run)"
fi

if [ "$run_omnifreight" = "1" ]; then
  echo "Invariant 2: omni_ops installs without budgeting"
  run omni_ops_alone     omni_ops            /omni_ops           "'omni_ops'" \
                         "'budgets','budgets_hr_expense','omni_budget'"
  run omni_budget_ontop  omni_budget         ""                  "'omni_ops','omni_budget','budgets','budgets_hr_expense'"
fi

if [ "$run_omnifreight" = "1" ]; then
  echo "Invariant 3: freight stack coexists"
  if [ -n "${ODOO_ENTERPRISE_PATH:-}" ]; then
    run freight_stack    omni_ops,omni_budget,ele_ap_validation,ele_bank_reconcile "" \
                         "'omni_ops','omni_budget','ele_ap_validation','ele_bank_reconcile'"
  else
    # ele_bank_reconcile requires Enterprise now, so this combination can only
    # be exercised in full on the enterprise run; drop it from the expected set
    # here rather than skip the scenario outright, so the other three modules'
    # coexistence still gets checked on every run.
    run freight_stack    omni_ops,omni_budget,ele_ap_validation "" \
                         "'omni_ops','omni_budget','ele_ap_validation'"
  fi
fi

if [ "$run_trading" = "1" ]; then
  run trading_budget     ele_trading_budget  /ele_trading_budget "'ele_trading','ele_trading_budget','budgets','budgets_hr_expense'"
fi

# Cross-vertical scenarios only make sense -- and only catch what they're
# meant to catch -- when BOTH verticals are in scope. Never drop them just
# because only one side changed: a change to one vertical's hooks is exactly
# what could break the other vertical's coexistence, so "only trading
# changed" is not a reason to skip checking trading against omnifreight.
if [ "$run_trading" = "1" ] && [ "$run_omnifreight" = "1" ]; then
  echo "Invariant 3b: both verticals coexist in one database"
  run both_verticals     ele_trading_budget,omni_budget ""       "'ele_trading_budget','omni_budget','omni_ops','ele_trading'"

  echo "Invariant 5: order.bridge.mixin/operations.budget.line hooks don't collide across verticals"
  run bridge_collision_regression \
      quotation,omni_ops,omni_budget,ele_trading,ele_trading_budget \
      /omni_ops,/omni_budget,/ele_trading,/ele_trading_budget \
      "'omni_ops','omni_budget','quotation','ele_trading','ele_trading_budget'"
fi

echo
if [ "$failures" -gt 0 ]; then
  echo "$failures scenario(s) FAILED"
  exit 1
fi
echo "all scenarios passed"
