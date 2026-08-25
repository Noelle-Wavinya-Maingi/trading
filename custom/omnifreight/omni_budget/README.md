# Freight Operations Budgets

Optional planned-vs-actual budgeting for freight manufacturing orders (files).
Each budget holds cost and revenue per service type (FOB / Freight /
Destination), can copy charges from the originating quotation, tracks margin,
and lets cost lines be actualised through expenses.

## Depends on
`omni_ops`, `budgets`, `budgets_hr_expense`, `budget_flag`

The `.text-expense-submitted` CSS class the budget list view uses lives
locally in this module (`static/src/css/budget_decoration.css`) — it used to
depend on the now-deleted `operations` module for that one file, but no
longer does.

## Why this is a separate module

Budgeting used to be wired into `omni_ops` itself — the budget fields, computes
and actions lived on that module's own `mrp.production` extension, and the
Budget tab lived in its form view. Core freight operations therefore could not
be installed without the whole budgeting feature.

This module inverts that dependency, mirroring how `trading_budget` layers onto
`trading`. Uninstalling it removes budgeting only; freight operations stay
intact, and `omni_ops` no longer depends on `budgets` at all.

## What this module adds

- **`omni.mrp.budget`**: one or more budgets per freight file, with budgeted vs.
  actual cost per service type and margin display.
- **The service-type split** on `operations.budget.line` (`service_type`:
  FOB / Freight / LOD) plus its `mrp_budget_id` anchor.
- **`omni.ops.file` extension**: `budget_ids`, `budget_id` (active budget),
  the create/view actions, and the Budget tab. (The `mrp.production`-based
  anchor and the `has_budget`/`budget_state` fields were retired in the
  Phase 5 process-engine migration; `has_budget` now comes from the shared
  `budget_flag` module instead of being defined here.)
- **`hr.expense` narrowing**: scopes selectable budget lines to the expense's own
  freight file.

## Anchor field naming

This module's anchor on the shared line model is **`mrp_budget_id`**, not
`budget_id`. `trading_budget` uses `ele_trade_budget_id`. Both bridges extend the
same `operations.budget.line`, so a shared name made the two verticals
mutually exclusive — see the naming rule in `budgets/README.md`.

Renaming that field ships a `migrations/19.0.1.0.1/pre-migrate.py`. **Existing
databases must be upgraded (`-u`), not just restarted**, or budget lines lose
their link to their budget.

## Design notes

- Amount syncing between an expense and its budget line comes from
  `budgets_hr_expense`; this module deliberately does not reimplement it. An
  earlier local copy shadowed the generic version and refreshed actual costs
  without the margin display.
- The FOB / Freight / LOD triad is still a Python `Selection` rather than
  configurable data, so a client with different service types needs a schema
  change. Tracked separately.
