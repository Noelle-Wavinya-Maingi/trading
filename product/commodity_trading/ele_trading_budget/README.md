# Trading Budget

Optional Trade Budget feature for the `ele_trading` module. Adds planned-vs-actual
cost/revenue tracking per trade, automatically synced from posted Bills,
Invoices, and Expenses.

## Depends on
`ele_trading`, `budgets`, `budgets_hr_expense`, `budget_flag`

## Why this is a separate module

Trade Budgets are installable and uninstallable independently of core
Trading. Ticking **Settings → Trading → Trade Budgets** installs this module
(pulling in `budgets`, `budgets_hr_expense`, and `budget_flag` automatically
as its own dependencies); unticking it uninstalls only this module, leaving
`ele_trading` and the budgets modules both untouched.

Every field and method this module adds to `trading.trade` (`budget_ids`,
`budget_id`, `action_create_budget`, `action_view_budget`, and the real
implementations of `_sync_budget_line_for_move`/`_remove_budget_line_for_move`)
is added via `_inherit`, layered on top of the no-op extension points already
defined in core `trading`.

## What this module adds

- **`trading.trade.budget`**: one budget per trade, holding Budgeted/Target
  Cost and Revenue, Actual Cost/Revenue, and variances against the trade's
  own Target Margin.
- **Budgeted vs. Target labeling**: for a Long trade, Cost is the known/quoted
  side (labeled "Budgeted") and Revenue is derived from the target margin
  (labeled "Target"); the reverse for a Short trade.
- **A merged `source_reference` column** showing whichever document (posted
  Bill/Invoice, or linked Expense) backs a given line.
- **Variance display gated on `is_fully_matched`**: cost/revenue variance is
  only shown once a trade is fully matched, since comparing "actual so far"
  against a whole-trade target isn't meaningful mid-trade.

## Automated tests
`tests/test_trading_margin.py` covers the target-margin/budget derivation
formulas for both Long and Short trades — the highest-risk financial logic in
this module.

## Design notes
- `source_reference` is a display-only field; the underlying document link
  is managed through the automatic Bill/Invoice/Expense sync, not edited
  directly through this column.