#!/bin/zsh
set -e

ODOO_ROOT="/Users/noellemaingi/Documents/odoo"
ENTERPRISE_ROOT="/Users/noellemaingi/enterprise"
TRADING_ROOT="/Users/noellemaingi/Documents/trading"

exec "$ODOO_ROOT/venv/bin/python" "$ODOO_ROOT/odoo-bin" \
  -d trading_demo \
  '--db-filter=^trading_demo$' \
  --addons-path="$ENTERPRISE_ROOT,$ODOO_ROOT/addons,$TRADING_ROOT/shared,$TRADING_ROOT/product/commodity_trading" \
  --http-port=8070
