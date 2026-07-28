# Trading

Core trade lifecycle, P&L, and target margin engine for commodity/goods
trading — buying, holding, and selling a position over time, across
currencies, as a single running trade rather than disconnected purchase and
sale documents.

## Depends on
`base`, `stock`, `sale`, `purchase`, `operations`, `hr_expense`, `base_setup`

## What this module does

- **Auto-creates/links a `trading.trade`** from confirmed Purchase Orders
  (Long trades) and Sale Orders (Short trades, or selling down an existing
  Long position).
- **Tracks position and P&L live**: open quantity, cost basis, realized and
  unrealized P&L, auto-closing the trade once purchase and sale quantities
  fully match.
- **Multi-currency by design**: purchase price, sale price, and market price
  each carry their own currency; everything converts to one reporting
  currency at the transaction's own date, keeping historical figures
  accurate regardless of when they're viewed.
- **Target Margin**: a trader sets an intended margin; the trade computes a
  target P&L and, for whichever side isn't already known (sale price for a
  Long trade, cover price for a Short trade), the price needed to hit it.
- **Stock lot linkage**: physical on-hand quantity is tracked independently
  from the commercial open position, since a confirmed sale and a validated
  goods receipt don't always happen at the same time.
- **Extension points for optional features**: `_sync_budget_line_for_move`
  and `_remove_budget_line_for_move` are no-ops in this module by default,
  overridden by `trading_budget` when that optional module is installed.
  Core Trading has no dependency on Trade Budgets.

## Key models

| Model | Role |
|---|---|
| `trading.trade` | Central record — identity, status, price/quantity, P&L, target margin |
| `trading.futures` | Optional forward/futures contract nested under a trade |

## Design notes
- `status` is a fixed three-value Selection (Draft/Confirmed/Closed) rather
  than a user-configurable pipeline. A CRM-style stage model is a reasonable
  future direction if more granular stages are needed.
- Additional costs/revenue from invoices and bills are tracked as an additive
  ledger on the trade (`additional_costs`/`additional_revenue`); each
  contributing line tracks exactly what it added, so edits and deletions
  reverse precisely rather than requiring a full recompute.