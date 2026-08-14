#!/usr/bin/env bash
#
# Fast local guardrail, run as a git pre-commit hook (installed via
# tools/install_hooks.sh). Catches the two classes of bug that reached a
# running dev server undetected on 2026-08-07:
#
#   1. Malformed XML (e.g. "--" inside a comment) -- caught by a plain
#      well-formedness parse, no Odoo needed.
#   2. Odoo API/field mismatches (e.g. ir.ui.menu.groups_id renamed to
#      group_ids in 19.0) -- only surfaces when the module actually loads,
#      so any staged module gets a real headless install/upgrade against a
#      throwaway database.
#   3. Two modules extending the same Odoo model with the same method name
#      and neither calling super() -- the exact shape that broke
#      order.bridge.mixin and operations.budget.line this cycle. A pure AST
#      scan (tools/check_extension_collisions.py), no Odoo needed either.
#
# tools/verify_boundaries.sh remains the authority on cross-module install
# invariants and runs in CI on every push; this script is deliberately
# narrower and faster so it's cheap enough to run on every commit.
#
# Usage: tools/pre_commit_check.sh
# Env:   ODOO_PATH, ODOO_PYTHON -- same meaning as verify_boundaries.sh.
set -uo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ODOO_PATH="${ODOO_PATH:-$HOME/Documents/odoo}"
ODOO_BIN="$ODOO_PATH/odoo-bin"
PYTHON="${ODOO_PYTHON:-$ODOO_PATH/venv/bin/python}"
PYTHON="$(command -v "$PYTHON" 2>/dev/null || true)"
HTTP_PORT="${HTTP_PORT:-8179}"

failures=0

staged_files() {
  # Include R (renamed/moved) alongside Added/Copied/Modified -- git detects
  # renames by default, and a plain ACM filter silently drops every moved
  # file, which is exactly the case (a directory move) this script most needs
  # to catch. --name-only prints only the new path for a rename, which is
  # what every caller below wants.
  git -C "$REPO" diff --cached --name-only --diff-filter=ACMR
}

STAGED=()
while IFS= read -r line; do
  [ -n "$line" ] && STAGED+=("$line")
done < <(staged_files)
[ "${#STAGED[@]}" -eq 0 ] && exit 0

# --- 0. Tripwire: nothing staged may change on disk while this hook runs ----
# A merge commit went through once with an incomplete tree even though every
# check here passed -- root cause was never pinned down for certain (this
# script itself only reads git plumbing and runs Odoo against a throwaway
# database, neither of which touches the working tree), but whatever the
# cause, the actual symptom was staged content silently drifting from what
# ended up committed. This closes that specific gap: hash every staged file
# before and after the checks below, and refuse to let the commit proceed if
# anything changed underneath it, regardless of why.
hash_staged() {
  for f in "${STAGED[@]}"; do
    [ -f "$REPO/$f" ] && printf '%s  %s\n' "$(git -C "$REPO" hash-object "$REPO/$f")" "$f"
  done
}

BEFORE_HASHES="$(hash_staged)"

_check_tripwire() {
  local after
  after="$(hash_staged)"
  if [ "$after" != "$BEFORE_HASHES" ]; then
    echo
    echo "FAIL  one or more staged files changed on disk during this hook's own checks:"
    diff <(printf '%s\n' "$BEFORE_HASHES") <(printf '%s\n' "$after") | sed 's/^/        /'
    echo
    echo "This is the exact anomaly that produced an incomplete merge commit once"
    echo "already. Do not commit -- re-stage and re-run this hook, and if it recurs,"
    echo "investigate before proceeding rather than retrying."
    exit 1
  fi
}
trap _check_tripwire EXIT

# --- 1. XML well-formedness on every staged .xml file -----------------------
xml_files=()
for f in "${STAGED[@]}"; do
  [[ "$f" == *.xml ]] && [ -f "$REPO/$f" ] && xml_files+=("$f")
done

if [ "${#xml_files[@]}" -gt 0 ]; then
  echo "Checking ${#xml_files[@]} staged XML file(s) are well-formed..."
  for f in "${xml_files[@]}"; do
    if ! python3 -c "import sys, xml.dom.minidom as m; m.parse(sys.argv[1])" "$REPO/$f" 2>/tmp/xmlerr; then
      echo "  FAIL  $f"
      sed 's/^/        /' /tmp/xmlerr
      failures=$((failures + 1))
    fi
  done
  rm -f /tmp/xmlerr
fi

if [ "$failures" -gt 0 ]; then
  echo
  echo "$failures XML file(s) failed to parse -- fix before committing."
  exit 1
fi

# --- 2. Cross-module method collisions (whole repo, not staged-file scoped --
# a collision is only visible with both sides in view, and the scan is fast
# enough to just always run it) ----------------------------------------------
py_staged=0
for f in "${STAGED[@]}"; do
  [[ "$f" == *.py ]] && py_staged=1 && break
done

if [ "$py_staged" -eq 1 ]; then
  if ! python3 "$REPO/tools/check_extension_collisions.py"; then
    echo
    echo "Fix the collision above before committing."
    exit 1
  fi
fi

# --- 3. Headless module load for any addon touched by this commit -----------
# Map a changed path to its top-level Odoo module directory, e.g.
# product/commodity_trading/ele_trading_budget/views/menu.xml -> ele_trading_budget.
# shared/ modules are one level deep (shared/<module>/...); product/ and
# custom/ modules are one level deeper, nested under a product-line or
# client-name folder (product/commodity_trading/<module>/..., matching
# custom/omnifreight/<module>/...).
modules=()
for f in "${STAGED[@]}"; do
  if [[ "$f" =~ ^shared/([^/]+)/ ]]; then
    mod="${BASH_REMATCH[1]}"
    [[ " ${modules[*]:-} " == *" $mod "* ]] || modules+=("$mod")
  elif [[ "$f" =~ ^(product|custom)/[^/]+/([^/]+)/ ]]; then
    mod="${BASH_REMATCH[2]}"
    [[ " ${modules[*]:-} " == *" $mod "* ]] || modules+=("$mod")
  fi
done

if [ "${#modules[@]}" -eq 0 ]; then
  echo "No addon module files staged -- skipping module load check."
  exit 0
fi

if [ -z "$PYTHON" ] || [ ! -f "$ODOO_BIN" ]; then
  echo "warning: Odoo not found (set ODOO_PATH/ODOO_PYTHON) -- skipping module load check for: ${modules[*]}"
  echo "         tools/verify_boundaries.sh will still catch this in CI, but slower."
  exit 0
fi

# See tools/verify_boundaries.sh for why ODOO_ENTERPRISE_PATH is optional
# and prepended rather than required.
ADDONS="$ODOO_PATH/addons,$REPO/shared,$REPO/product/commodity_trading,$REPO/custom/omnifreight,$REPO/third_parties"
if [ -n "${ODOO_ENTERPRISE_PATH:-}" ]; then
  ADDONS="$ODOO_ENTERPRISE_PATH,$ADDONS"
fi
install_list="$(IFS=,; echo "${modules[*]}")"
db="precommit_$$"

echo "Loading module(s) [$install_list] against a throwaway database..."
dropdb --if-exists "$db" >/dev/null 2>&1
createdb "$db" >/dev/null 2>&1

out=$("$PYTHON" "$ODOO_BIN" -d "$db" --addons-path="$ADDONS" -i "$install_list" \
      --stop-after-init --http-port="$HTTP_PORT" --log-level=warn 2>&1)

dropdb --if-exists "$db" >/dev/null 2>&1

bad=$(printf '%s' "$out" | grep -cE "CRITICAL|ParseError|Failed to (load|initialize)|Traceback")
if [ "$bad" -gt 0 ]; then
  echo "  FAIL  module load raised errors:"
  printf '%s' "$out" | grep -E "CRITICAL|ParseError|Failed to (load|initialize)|Error:" | head -8 | sed 's/^/        /'
  echo
  echo "Fix the above before committing -- these break every module that depends on [$install_list]."
  exit 1
fi

echo "  ok    [$install_list] loaded cleanly"
