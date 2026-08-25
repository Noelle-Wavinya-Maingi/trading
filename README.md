# Trading Suite (Custom Odoo Addons)

Custom Odoo 19 modules: trade lifecycle & P&L, target margin, the optional
Trade Budgets feature, freight operations, and the shared budget layer they
all build on.

## Requirements

This repo contains only custom addon code. It requires:
- Odoo 19.0 Community core (not included here)
- PostgreSQL
- The addons-path roots below

## Repository layout

Modules are grouped by **who can use them and who owns them**, and every
module lives in exactly one group. The repository root holds no modules at
all — only this README and tooling config — so the group folders are the
addons-path roots.

**The group folders are addons-path roots, not Python packages.** They
deliberately contain no `__init__.py` or `__manifest__.py`. Odoo modules are
always top-level packages under an addons-path entry; they are never
sub-packages of a container directory. Every module therefore uses ordinary
`from . import x` imports.

```
shared/              <- root #1: reusable infrastructure, no vertical coupling
├── budgets/                shared budget line model
├── budgets_hr_expense/     optional hr.expense actualization backend
├── dispatch/  order-confirmation -> operational-record mixin
├── workflow/   generic operational-steps/template engine
└── budget_flag/         shared "has_budget" mixin

product/ap_validation/       <- root #2: Elewa-owned resale products, one root per product line
└── ele_ap_validation/     vendor bill approval workflow

product/bank_reconciliation/ <- root #3
└── ele_bank_reconcile/    bank statement match classification

product/commodity_trading/   <- root #4
├── ele_trading/
└── ele_trading_budget/

custom/omnifreight/           <- root #5: bespoke work built for one specific client
├── omni_ops/
├── omni_budget/
└── quotation/

third_parties/         <- root #6: vendored/purchased modules not authored by Elewa
                           (empty today; see third_parties/README.md)
```

Each subfolder under `product/` and `custom/` (e.g. `product/commodity_trading/`,
`custom/omnifreight/`) is its own addons-path root — `product/` and `custom/`
themselves are just organizing directories, not roots you point Odoo at.

The placement rule is a claim you can test: anything in `shared/` must install
on a database with no vertical module present. `ele_ap_validation` and
`ele_bank_reconcile` install against `account` (plus `hr_expense`) alone,
pulling in no freight, MRP or budgeting — but both are standalone resale
products in their own right, not infrastructure other modules build on, which
is why they live under `product/` rather than `shared/`.

`product/` vs. `custom/` is about ownership and reuse intent, not code
quality: `product/commodity_trading` has no client attached and is meant to
be sold as-is to whoever signs next, while `custom/omnifreight` is bespoke
work for one client — bridge modules built for a *future* second client
belong in their own `custom/<client-name>/` folder, never by editing a
product module to fit one customer.

**Product naming.** Modules intended for resale use the vendor prefix `ele_`
(Elewa), not a client's name. `ele_bank_reconcile`, `ele_ap_validation`,
`ele_trading` and `ele_trading_budget` have all been renamed accordingly —
done while their install base is still zero, since a module rename changes
every XML ID it owns.

**`operations` has been deleted.** It failed the placement rule above — it
installed the literal module names `'quotation'` and `'trading'` from its own
settings, so the "shared" layer reached back into both verticals — and nothing
in the repository referenced any of its models or config fields. `trading` and
`omni_ops` each declared it as a dependency neither actually used; both
dependencies are gone, and the one real thing it provided externally (a CSS
class for the budget line list) moved into `omni_budget`, its only real
consumer. See [docs/ARCHITECTURE_ROADMAP.md](docs/ARCHITECTURE_ROADMAP.md)
§Tier 4 for the analysis that led to this.

### Running Odoo against this repo

```bash
odoo-bin -d <db> --addons-path=<odoo>/addons,<repo>/shared,<repo>/product/ap_validation,<repo>/product/bank_reconciliation,<repo>/product/commodity_trading,<repo>/custom/omnifreight,<repo>/third_parties
```

All six roots are required (`third_parties/` is harmless to include even
while empty). Omitting a root makes the modules under it invisible, and any
module depending on them will fail to install. Note the repository root
itself is **not** an addons path.

## Modules

**`shared/` — usable by any client**
- `budgets` — industry-agnostic budget line model, no `hr_expense` dependency
- `budgets_hr_expense` — optional actualization backend: auto-syncs an
  `hr.expense` to a budget line's actual amount
- `dispatch` — `dispatch.mixin`: confirm-order -> derive-operational-
  record template, shared by trading (sale/purchase) and freight (quotation)
- `workflow` — generic operational-steps/sequencing/template engine,
  independent of `mrp`
- `budget_flag` — `budget.flag.mixin`: shared computed `has_budget` flag,
  consumed by each vertical's own budget bridge module

**`product/ap_validation/`, `product/bank_reconciliation/`, `product/commodity_trading/` — Elewa-owned resale products**
- `ele_ap_validation` — vendor bill approval workflow (depends on `account`,
  `hr_expense`)
- `ele_bank_reconcile` — bank statement match classification (depends on
  `account`, `account_accountant`; Enterprise only)
- `ele_trading` — core trade lifecycle, P&L, target margin
- `ele_trading_budget` — optional Trade Budget feature (bridge onto `budgets`)

**`custom/omnifreight/` — freight client**
- `omni_ops` — freight operations engine on `workflow` (files, service
  templates, work orders, vessels, documents)
- `omni_budget` — optional planned-vs-actual budgeting per freight file
  (bridges `omni_ops` onto `budgets`)
- `quotation` — freight quotation, routes, rates, carriers

## Record-level security

Every model that owns its own row of business data (not a pure line-item
attached to an already-secured header) has a multi-company `ir.rule`, mirroring
Odoo's own `account_security.xml` convention: no `groups` attribute, domain
keyed off `company_id in company_ids`.

- `trading.trade`, `trading.trade.step`, `trading.futures`,
  `trading.future.delivery.line` (`ele_trading`) and `trading.trade.budget`
  (`ele_trading_budget`) each have their own rule — see
  `product/commodity_trading/*/security/ir_rules.xml`.
- `operations.budget.line` (`shared/budgets`) has a rule too, keyed on a
  `company_id` computed through the anchor-provider registry rather than a
  hardcoded anchor field name, so it works whether or not any vertical is
  installed — see `shared/budgets/security/ir_rules.xml`.
- `ele_ap_validation` and `ele_bank_reconcile` add no rules of their own: they
  only extend `account.move`, `hr.expense`, and `account.bank.statement.line`,
  all of which already ship native multi-company rules in Odoo core
  (`account/security/account_security.xml`, `hr_expense/security/`). Adding a
  redundant rule there would only risk double-filtering.

## Running the tests

```bash
odoo-bin -d <db> --addons-path=... -i <module> --test-enable --test-tags=/<module> --stop-after-init
```

**Important test-isolation rule.** The `budgets` and `budgets_hr_expense`
suites test the shared model *standalone* and must run in a database with
**no client bridge module installed**. Both `ele_trading_budget` and
`omni_budget` add a **required** anchor field to `operations.budget.line`
(`ele_trade_budget_id` / `mrp_budget_id`), so once either is installed a bare
budget line can no longer be created and those suites fail with a not-null
violation. Give them their own database:

| Suite | Install | Must NOT also install |
|---|---|---|
| `/budgets` | `budgets` | any bridge or backend |
| `/budgets_hr_expense` | `budgets_hr_expense` | any client bridge |
| `/ele_trading_budget` | `ele_trading_budget` | — |

The two verticals **can** share a database. They could not until their anchor
fields were namespaced — both previously defined `budget_id` pointing at
different models, which broke `ele_trading_budget`'s `trade_id` related field
at registry build. See the naming rule in
[shared/budgets/README.md](shared/budgets/README.md).

### Verifying the architecture

`tools/verify_boundaries.sh` checks the invariants the layout claims — that
`shared/` modules install with no vertical present, that `omni_ops` installs
without budgeting, and that both verticals coexist:

```bash
ODOO_PATH=/path/to/odoo tools/verify_boundaries.sh
```
