# Budgets

Shared, industry-agnostic budget line model. Provides one reusable
`operations.budget.line` model that any business-domain module can build a
budget feature on top of, without duplicating the underlying line logic.

## Depends on
`base`, `mail`, `account`, `hr_expense`

## Design principle

This module carries no anchor field of its own — no `trade_id`,
`production_id`, or any reference to a specific business domain. Each
industry module adds its own anchor via `_inherit`, and overrides a small set
of hook methods to plug itself in:

| Hook | Purpose |
|---|---|
| `_get_anchor_record()` | The parent business record this line belongs to (for chatter/validation) |
| `_get_anchor_expense_vals()` | Extra vals merged into an auto-created `hr.expense` |
| `_get_display_name_prefix()` | Prefix used when formatting an auto-generated expense's name |
| `_notify_anchor_of_amount_change()` | Recompute the anchor's own aggregates when a line's amount changes |
| `_get_conversion_company()` / `_get_target_currency()` | Currency conversion context |

**Current consumers:** `trading_budget` (`trading.trade.budget`) and
`omni_ops` (`omni.mrp.budget`) each `_inherit` this model to add their own
anchor and hook implementations.

## What this module provides directly

- **Section/note rows** (`display_type`), following the same convention as
  `sale.order.line`/`purchase.order.line`.
- **Automatic expense creation/reversal**: a cost-side line with a positive
  actual amount and no linked invoice/bill auto-creates a backing
  `hr.expense`; this is undone if the line's amount drops to zero or a
  document gets linked instead.
- **`hr.expense` integration**: `budget_line_id` on `hr.expense`, with
  bidirectional amount/date syncing.

## Design guideline for extending this module
Any field referencing a specific business domain (a trade, a production
order, etc.) belongs in that domain's own bridge module, not in `budgets`
itself. Keeping this model anchor-free is what allows it to be shared across
multiple industries without one industry's assumptions leaking into another.