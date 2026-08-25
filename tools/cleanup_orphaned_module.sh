#!/usr/bin/env bash
#
# Cleanly uninstalls a module that has been renamed or retired, so its stale
# ir_module_module record and any data it owns don't linger in a database
# under the old name. See docs/MIGRATIONS.md's "orphaned module cleanup
# runbook" for the manual, step-by-step version of what this wraps.
#
# Usage:
#   ODOO_PATH=/path/to/odoo tools/cleanup_orphaned_module.sh <module_name> <db_name>
#
set -uo pipefail

ODOO_PATH="${ODOO_PATH:-$HOME/Documents/odoo}"
ODOO_BIN="$ODOO_PATH/odoo-bin"
PYTHON="${ODOO_PYTHON:-$ODOO_PATH/venv/bin/python}"
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# `[ -x "$PYTHON" ]` only checks a literal path, not a $PATH lookup, so
# ODOO_PYTHON=python (a bare command name, as used in CI with no venv) would
# fail that check even though `python` resolves fine. `command -v` handles
# both a bare command and an explicit path, matching verify_boundaries.sh.
PYTHON="$(command -v "$PYTHON" 2>/dev/null || true)"

MODULE="${1:-}"
DB="${2:-}"

if [ -z "$MODULE" ] || [ -z "$DB" ]; then
  echo "usage: $0 <module_name> <db_name>" >&2
  exit 2
fi

if [ -z "$PYTHON" ] || [ ! -f "$ODOO_BIN" ]; then
  echo "error: Odoo not found. Set ODOO_PATH (currently '$ODOO_PATH') and/or ODOO_PYTHON." >&2
  exit 2
fi

ADDONS="${ADDONS_PATH:-$ODOO_PATH/addons,$REPO/shared,$REPO/product/commodity_trading,$REPO/product/ap_validation,$REPO/product/bank_reconciliation,$REPO/custom/omnifreight,$REPO/third_parties}"

# If <module_name> still resolves to real module code on the addons path,
# this is not an orphan cleanup -- it's a live module, and
# button_immediate_uninstall() below would just tear it down and let Odoo's
# own upgrade logic reinstall/reprocess it under its old name on the next -u,
# instead of leaving it cleanly removed. Manifest presence is checked the
# same way Odoo itself discovers modules: a __manifest__.py directly under a
# directory named for the module, somewhere on the addons path.
IFS=',' read -ra ADDONS_DIRS <<< "$ADDONS"
for dir in "${ADDONS_DIRS[@]}"; do
  if [ -f "$dir/$MODULE/__manifest__.py" ]; then
    echo "error: '$MODULE' still resolves to real module code at $dir/$MODULE -- this is not an orphan. Remove the code or update the addons path before cleaning up its database record." >&2
    exit 2
  fi
done

STATE=$(PGDATABASE="$DB" psql -tAc "select state from ir_module_module where name = '$MODULE'" 2>/dev/null)

if [ -z "$STATE" ]; then
  echo "'$MODULE' has no ir_module_module record in '$DB' -- nothing to clean up."
  exit 0
fi

if [ "$STATE" = "uninstalled" ]; then
  echo "'$MODULE' is already uninstalled in '$DB' -- nothing to do."
  exit 0
fi

echo "Uninstalling '$MODULE' (state: $STATE) from '$DB'..."

"$PYTHON" "$ODOO_BIN" shell --no-http -d "$DB" --addons-path="$ADDONS" <<PYEOF
module = env['ir.module.module'].search([('name', '=', '$MODULE')])
if not module:
    print("'$MODULE' not found in ir_module_module -- nothing to do.")
elif module.state == 'uninstalled':
    print("'$MODULE' is already uninstalled.")
else:
    module.button_immediate_uninstall()
    env.cr.commit()
    print("Uninstalled '$MODULE'.")
PYEOF
