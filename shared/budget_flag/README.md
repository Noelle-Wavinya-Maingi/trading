# Budget Flag Bridge Mixin

Shared `has_budget`/`budget_state` pair and a reusable budget-header mixin,
extracted after two verticals (`trading_budget`, `omni_budget`) independently
duplicated the exact same field pair on their own anchor models.

## Depends on
`base`

## What it provides

- **`budget.flag.mixin`** — include on an anchor model (`trading.trade`, a
  freight file) that tracks budgets. Supplies:
  - `has_budget`, computed from a `budget_ids` One2many the including model
    must define itself under that exact name.
  - `budget_state`, computed from `budget_id.state` — the including model
    must also define `budget_id` (singular, the "active" budget among
    `budget_ids`) under that exact name, stored.

  Both field names are hardcoded in the mixin's own `@api.depends()`, the
  same way Odoo's own conventional field names are load-bearing — renaming
  `budget_ids`/`budget_id` on an including model breaks the mixin's compute
  at registry build time, it does not just look wrong.

  Also provides `_bridge_open_budget_action(budget)`, returning a form-view
  action for the given budget (raises `ValidationError` if none).

- **`budget.document.mixin`** — include on a budget *header* model
  (`trading.trade.budget`, a freight budget). Supplies `name` (auto-numbered
  via `_budget_sequence_code()`, which the including model must override),
  `currency_id`, `company_id`, `state` (draft/confirmed/closed), and
  `action_confirm()`/`action_close()`.

**Current consumers:** `ele_trading_budget` (`trading.trade` +
`trading.trade.budget`) and `omnifreight`'s `omni_budget` (its own anchor +
budget header). Each vertical's anchor field on `operations.budget.line`
itself is namespaced separately — see
[shared/budgets/README.md](../budgets/README.md#naming-rule-for-a-bridges-anchor-field).

## Automated tests

`tests/test_budget_bridge_mixin.py` exercises `has_budget`/`budget_state`,
the confirm/close transitions, reference generation, and
`_bridge_open_budget_action()` against a test-only host/document model set
in `models/` (not `tests/`, for the same registry-timing reason as
`dispatch`'s test host).
