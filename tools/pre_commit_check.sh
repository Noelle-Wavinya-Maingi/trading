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

# --- 2. Headless module load for any addon touched by this commit -----------
# Map a changed path to its top-level Odoo module directory, e.g.
# commodity_trading/trading_budget/views/menu.xml -> trading_budget.
modules=()
for f in "${STAGED[@]}"; do
  if [[ "$f" =~ ^(commodity_trading|shared)/([^/]+)/ ]]; then
    mod="${BASH_REMATCH[2]}"
    [[ " ${modules[*]:-} " == *" $mod "* ]] || modules+=("$mod")
  elif [[ "$f" =~ ^client/omnifreight/([^/]+)/ ]]; then
    mod="${BASH_REMATCH[1]}"
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
ADDONS="$ODOO_PATH/addons,$REPO/shared,$REPO/commodity_trading,$REPO/client/omnifreight"
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
