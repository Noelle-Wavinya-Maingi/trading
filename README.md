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

Modules are grouped by **who can use them**, and every module lives in exactly
one group. The repository root holds no modules at all — only this README and
tooling config — so the three group folders are the addons-path roots.

**The group folders are addons-path roots, not Python packages.** They
deliberately contain no `__init__.py` or `__manifest__.py`. Odoo modules are
always top-level packages under an addons-path entry; they are never
sub-packages of a container directory. Every module therefore uses ordinary
`from . import x` imports.

```
shared/              <- root #1: reusable by ANY client, no vertical coupling
├── budgets/                shared budget line model
├── budgets_hr_expense/     optional hr.expense actualization backend
├── operations/             shared config / industry / workflow layer
├── omni_ap_validation/     vendor bill approval workflow
└── omni_bank_reconcile/    bank statement match classification

commodity_trading/   <- root #2: commodity trading client
├── trading/
└── trading_budget/

omnifreight/         <- root #3: freight client
├── omni_ops/
├── omni_budget/
└── quotation/
```

The placement rule is a claim you can test: anything in `shared/` must install
on a database with no vertical module present. `omni_ap_validation` and
`omni_bank_reconcile` earn their place there — each installs against `account`
(plus `hr_expense`) alone, pulling in no freight, MRP or budgeting.

> **Naming debt:** those two still carry an `omni_` prefix from when they lived
> inside the freight module. The prefix is now misleading, but renaming an Odoo
> module changes every XML ID it owns and needs a rename migration, so it is
> deliberately deferred rather than done casually.

> **`operations` fails the rule above and its placement here is provisional.**
> It installs the literal module names `'quotation'` and `'trading'` from its
> settings (`models/config_settings.py:198`), so the shared layer reaches back
> into both verticals. It sits here only because `trading` and `omni_ops` still
> declare it as a dependency — a dependency neither actually uses. See
> [docs/ARCHITECTURE_ROADMAP.md](docs/ARCHITECTURE_ROADMAP.md) §Tier 4; the
> recommendation is to delete it.

### Running Odoo against this repo

```bash
odoo-bin -d <db> --addons-path=<odoo>/addons,<repo>/shared,<repo>/commodity_trading,<repo>/omnifreight
```

All three roots are required. Omitting one makes the modules under it
invisible, and any module depending on them will fail to install. Note the
repository root itself is **not** an addons path.

## Modules

**`shared/` — usable by any client**
- `budgets` — industry-agnostic budget line model, no `hr_expense` dependency
- `budgets_hr_expense` — optional actualization backend: auto-syncs an
  `hr.expense` to a budget line's actual amount
- `operations` — shared configuration, industry config, workflow stages
- `omni_ap_validation` — vendor bill approval workflow (depends on `account`,
  `hr_expense`)
- `omni_bank_reconcile` — bank statement match classification (depends on
  `account`)

**`commodity_trading/` — commodity trading client**
- `trading` — core trade lifecycle, P&L, target margin
- `trading_budget` — optional Trade Budget feature (bridge onto `budgets`)

**`omnifreight/` — freight client**
- `omni_ops` — freight operations on top of MRP (files, BOMs, service
  templates, work orders, vessels, documents)
- `omni_budget` — optional planned-vs-actual budgeting per freight file
  (bridges `omni_ops` onto `budgets`)
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
