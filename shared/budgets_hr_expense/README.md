# Budgets - HR Expense Actualization

Optional actualization backend for the shared `budgets` module. A cost-side
`operations.budget.line` with a positive actual amount and no linked
invoice/bill auto-creates a backing `hr.expense`; this is undone if the
line's amount drops to zero or an invoice/bill gets linked instead.

## Depends on
`budgets`, `hr_expense`

## Why this is a separate module

`budgets` itself has no opinion on how a line's actual amount gets realized
-- it only calls a no-op hook, `_sync_actual_source()`, whenever a line's
amount or source changes. This module is one implementation of that hook,
built on `hr.expense`.

Install it only for clients whose actual-cost trail should run through
Expenses. A client tracking actuals purely via `actual_amount` /
`account_move_id` (posted bills), or through some other mechanism entirely,
can skip this module and either implement their own `_sync_actual_source()`
override, or use none at all -- `budgets` works standalone either way.
Uninstalling this module leaves `budgets` fully intact.

## What this module adds

- **`expense_id` / `expense_is_submitted`** on `operations.budget.line`.
- **Auto-create/update/unlink**: `_sync_actual_source()` creates an
  `hr.expense` when a cost-side line gets a positive actual amount, keeps it
  in sync while the line changes, and removes it if the amount drops to zero
  or an invoice/bill takes over instead.
- **`ele_budget_line_id`** on `hr.expense`, with bidirectional amount/date sync
  back onto the linked line.
- **`source_reference` extension**: adds `hr.expense` as a possible value
  alongside the `account.move` option already provided by `budgets`.

## Design notes

- Requires the acting user to have an `hr.employee` record (a property of
  this specific mechanism -- posting an `hr.expense` needs one -- not a
  requirement of budgeting in general).
- Requires the consuming module's anchor to supply a non-empty
  `_get_anchor_link_vals()`; a bare `operations.budget.line` with no anchor
  (the base module's own default) will raise rather than silently create an
  orphaned expense.

## Automated tests

**Run these in a database with no client bridge installed** (`budgets` +
`budgets_hr_expense` only). `ele_trading_budget` and `omni_budget` each add a
*required* anchor field to `operations.budget.line` (`ele_trade_budget_id` and
`mrp_budget_id` respectively), which makes the bare lines these tests create
impossible to insert.

`tests/test_operations_budget_line.py` covers the create/update/unlink
lifecycle of the auto-managed expense: no expense for a zero amount, blocked
without an anchor, created once anchored, removed when the amount drops to
zero, removed when an invoice/bill is linked instead, and never created for
revenue (`charge`) lines.
