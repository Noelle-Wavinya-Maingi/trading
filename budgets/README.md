# Budgets

Shared, industry-agnostic budget line model. Provides one reusable
`operations.budget.line` model that any business-domain module can build a
budget feature on top of, without duplicating the underlying line logic.

## Depends on
`base`, `mail`, `account`

This module has **no dependency on `hr_expense`** or any other mechanism for
realizing a line's actual amount. If you want auto-created expenses backing
budget lines, install the separate `budgets_hr_expense` module alongside it
(see below) — `budgets` itself works standalone for a client that tracks
actuals purely via `actual_amount`/`account_move_id`.

## Design principle

This module carries no anchor field of its own — no `trade_id`,
`production_id`, or any reference to a specific business domain. Each
industry module adds its own anchor via `_inherit`, and overrides a small set
of hook methods to plug itself in:

| Hook | Purpose |
|---|---|
| `_get_anchor_record()` | The parent business record this line belongs to (for chatter/validation). Must return either an empty recordset (no anchor) or a record that inherits `mail.thread` -- enforced at write time by `_check_anchor_supports_chatter()`, which raises a clear error rather than letting an incompatible anchor fail with an opaque `AttributeError` |
| `_get_anchor_link_vals()` | Extra vals identifying this line's anchor, merged into any backing document an actualization backend creates |
| `_get_display_name_prefix()` | Prefix used when formatting an auto-generated backing document's name |
| `_notify_anchor_of_amount_change()` | Recompute the anchor's own aggregates when a line's amount changes |
| `_get_conversion_company()` / `_get_target_currency()` | Currency conversion context |
| `_sync_actual_source()` | Create/update/remove whatever document backs this line's actual amount. No-op by default -- this is what an actualization backend module (like `budgets_hr_expense`) overrides |

**Current consumers:** `trading_budget` (`trading.trade.budget`) and
`omni_ops` (`omni.mrp.budget`) each `_inherit` this model to add their own
anchor and hook implementations. Both also depend on `budgets_hr_expense`
for auto-expense creation.

## What this module provides directly

- **Section/note rows** (`display_type`), following the same convention as
  `sale.order.line`/`purchase.order.line`.
- **Invoice/bill linking**: `account_move_id` lets a line say "my actual
  amount is already represented by this posted document" instead of
  entering an amount manually.
- The `_sync_actual_source()` extension point for a backend to auto-realize
  a line's actual amount as some other document (an expense, a different
  kind of record, etc.) — `budgets` itself takes no position on how that
  happens.

## `budgets_hr_expense` (optional actualization backend)

A separate addon, `budgets_hr_expense`, depends on `budgets` + `hr_expense`
and overrides `_sync_actual_source()` to auto-create/update/remove a linked
`hr.expense` as a line's actual amount changes, plus `budget_line_id` on
`hr.expense` with bidirectional amount/date syncing. Install it only for
clients whose actual-cost trail should run through Expenses; a client using
vendor bills, bank reconciliation, or any other mechanism can skip it
entirely and implement their own backend the same way.

## Automated tests

**Run these in a database with no bridge/backend installed.** Both
`trading_budget` and `omni_ops` add a *required* `budget_id` to
`operations.budget.line`, so once either is installed a bare line can no
longer be created and every test here fails with a not-null violation. This
is a property of the test context, not a defect — but it means a CI job for
`/budgets` must install `budgets` alone.

`tests/test_operations_budget_line.py` covers the core model standalone (no
bridge module, no actualization backend installed): section/note
constraints, variance/currency computation, `source_reference`, the default
hooks being true no-ops, and the anchor chatter contract -- both the happy
path (a `mail.thread` anchor gets tracking messages) and the guarded failure
(a non-chatter anchor raises a clear `ValidationError` instead of crashing
inside `message_post()`).

## Design guideline for extending this module

Any field referencing a specific business domain (a trade, a production
order, etc.) belongs in that domain's own bridge module, not in `budgets`
itself. Keeping this model anchor-free and mechanism-free (no assumption
about *how* actuals get realized) is what allows it to be shared across
multiple industries and multiple clients without one client's assumptions
leaking into another.
