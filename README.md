# Trading Suite (Custom Odoo Addons)

Custom Odoo 19 modules: trade lifecycle & P&L, target margin, the optional
Trade Budgets feature, freight operations, and the shared budget/operations
layer they all build on.

## Requirements

This repo contains only custom addon code. It requires:
- Odoo 19.0 Community core (not included here)
- PostgreSQL
- The three addons-path roots below

## Repository layout

Modules are grouped by who owns them. **The grouping folders
(`commodity_trading/`, `omnifreight/`) are addons-path roots, not Python
packages** — they deliberately contain no `__init__.py` or `__manifest__.py`.
Odoo modules are always top-level packages under an addons-path entry; they
are never sub-packages of a container directory. Every module therefore uses
ordinary `from . import x` imports.

```
.                        <- addons-path root #1: shared, client-agnostic
├── budgets/                 shared budget line model
├── budgets_hr_expense/      optional hr.expense actualization backend
├── operations/              shared config/industry/workflow layer
│
├── commodity_trading/   <- addons-path root #2: commodity trading vertical
│   ├── trading/
│   └── trading_budget/
│
└── omnifreight/         <- addons-path root #3: freight vertical
    ├── omni_ops/
    └── quotation/
```

### Running Odoo against this repo

```bash
odoo-bin -d <db> --addons-path=<odoo>/addons,<repo>,<repo>/commodity_trading,<repo>/omnifreight
```

All three roots are required. Omitting one makes the modules under it
invisible, and any module depending on them will fail to install.

## Modules

**Shared (addons-path root)**
- `budgets` — industry-agnostic budget line model, no `hr_expense` dependency
- `budgets_hr_expense` — optional actualization backend: auto-syncs an
  `hr.expense` to a budget line's actual amount
- `operations` — shared configuration, industry config, workflow stages

**Commodity trading vertical**
- `trading` — core trade lifecycle, P&L, target margin
- `trading_budget` — optional Trade Budget feature (bridge onto `budgets`)

**Freight vertical**
- `omni_ops` — freight operations on top of MRP, plus budgeting, AP
  validation and bank reconciliation
- `quotation` — freight quotation, routes, rates, carriers

## Running the tests

```bash
odoo-bin -d <db> --addons-path=... -i <module> --test-enable --test-tags=/<module> --stop-after-init
```

**Important test-isolation rule.** The `budgets` and `budgets_hr_expense`
suites test the shared model *standalone* and must run in a database with
**no client bridge module installed**. Both `trading_budget` and `omni_ops`
add a **required** `budget_id` to `operations.budget.line`, so once either is
installed a bare budget line can no longer be created and those suites fail
with a not-null violation. Give them their own database:

| Suite | Install | Must NOT also install |
|---|---|---|
| `/budgets` | `budgets` | any bridge or backend |
| `/budgets_hr_expense` | `budgets_hr_expense` | any client bridge |
| `/trading_budget` | `trading_budget` | `omni_ops` |

`trading_budget` and `omni_ops` **cannot currently share a database** — both
define `budget_id` on `operations.budget.line` pointing at different models,
which breaks `trading_budget`'s `trade_id` related field at registry build.
Each vertical is expected to run in its own database.
