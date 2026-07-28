# Trading Suite (Custom Odoo Addons)

Custom Odoo 19 modules: trade lifecycle & P&L, target margin, the optional
Trade Budgets feature, and shared operational tooling.

## Requirements
This repo contains only custom addon code. It requires:
- Odoo 19.0 Community core (not included here)
- These modules placed on Odoo's `--addons-path`

## Modules
- `trading` — core trade lifecycle, P&L, target margin
- `trading_budget` — optional Trade Budget feature (bridge module)
- `budgets` — shared, industry-agnostic budget line model
- `operations`, `omni_ops`, `quotation` — supporting freight/manufacturing modules
