# Trading & Budgets: Hardening Plan

**Status:** draft for review
**Author:** Elewa Company Limited
**Date:** 6 August 2026
**Scope:** `commodity_trading/trading`, `commodity_trading/trading_budget`,
`shared/budgets`, `shared/budgets_hr_expense`.

---

## 0. Executive summary

This is the trading-side equivalent of the Omnifreight restructure plan
(`docs/ARCHITECTURE_ROADMAP.md`), but the starting position is much better, so the
plan is much shorter. Trading was never a vendored Odoo fork — there is no
repo-shape problem, no monorepo migration, and no database-migration mechanics
to work out. What follows are the sections of that methodology that actually
apply here: mixin composition, file/model naming, manifest hygiene, i18n, a
security model, and test coverage.

Findings, in one line each:

- **Mixin composition is already correct.** No Python-multiple-inheritance
  mixins exist anywhere in these four modules — unlike Omnifreight's original
  `class X(models.Model, SomeMixin)` pattern, every model here is a plain
  `class X(models.Model):` with Odoo mixins (`mail.thread`,
  `mail.activity.mixin`) composed via `_inherit = [...]`. Nothing to fix.
- **Security is the real gap.** Zero `ir.rule` records anywhere in scope, and
  every `ir.model.access.csv` row grants `base.group_user` full CRUD including
  unlink. This is the same finding the Omnifreight roadmap already flagged for
  the freight side (D4) — it is equally true here and gates nothing else, so
  it can start now.
- **Tests are inverted against risk, same shape as before the freight-side
  Phase 2 work.** `trading` — the largest, most logic-dense module — has
  **zero** tests. `trading_budget` covers only margin math. `shared/budgets`
  and `shared/budgets_hr_expense` are comparatively well tested already.
- **A handful of mechanical naming/quality fixes remain** from the rename pass
  already done this session (`purchare_order.py` → `purchase_order.py`,
  `futures.py` → `trading_futures.py`, `stock.py` → `stock_picking.py`,
  `trading_trade_budget_line.py` → `operations_budget_line.py`): one file still
  bundles two models (`trading_futures.py`), inline CSS styling is duplicated
  across two view files, and five chatter/note messages use f-strings instead
  of `_()`.
- **Manifest hygiene is already clean** — correct author/website/licence/version
  on all four, no scaffold defaults. Minor nits only.

Nothing here is blocked on a business decision the way the freight side was
blocked on D1–D4. This plan can run start to finish without further sign-off,
except where noted in §5.

---

## 1. Findings by dimension

### 1.1 Mixin composition — clean, nothing to adopt

`grep`ing every model class definition across all four modules for Python
multiple inheritance (`class X(models.Model, SomeMixin)`) returns nothing.
Every mixin composition already uses the correct Odoo pattern:

```python
# commodity_trading/trading/models/trading_trade.py:9-11
_name = 'trading.trade'
_inherit = ['mail.thread', 'mail.activity.mixin']
```

Same pattern in `trading/models/futures.py`, `trading_budget/models/trading_trade_budget.py`,
and `shared/budgets/models/operations_budget_line.py`.

**Gap, not a defect:** no shared `AbstractModel` mixin exists for currency
conversion — every model that needs it (`account_move_trade_pnl.py`,
`trading_trade_pnl.py`) hand-rolls its own rate lookup. This is the same shape
of problem the freight-side roadmap is already fixing via
`shared/currency_conversion` (Phase 2 item 8). Once that module has real
content, `trading`'s duplicated conversion logic is a second consumer worth
migrating onto it — but that's downstream of the freight-side work landing
first, not blocking anything here.

**Action:** none required. Revisit currency-conversion dedup once
`shared/currency_conversion` has model code (tracked separately, not in this
plan).

### 1.2 File/model naming

Already substantially fixed this session (the `purchare_order.py`,
`futures.py`, `stock.py`, `trading_trade_budget_line.py` renames). Remaining:

| Issue | File | Fix |
|---|---|---|
| Two models in one file | `trading/models/trading_futures.py` — `trading.futures` (line 7) and `trading.future.delivery.line` (line 338) | Split into `trading_futures.py` + `trading_future_delivery_line.py` |
| Same filename across two modules | `trading/models/trading_trade.py` (defines `trading.trade`) vs. `trading_budget/models/trading_trade.py` (bridges it) | Not a bug — different Python packages — but a navigation hazard. Rename the bridge file to `trading_trade_budget_bridge.py` to disambiguate at a glance |
| Stale commented import | `trading/models/__init__.py:16` — `# from . import hr_expense`, referencing a file that doesn't exist in this module (it lives in `trading_budget`) | Delete the line |

### 1.3 Model namespacing

All `trading.*` model names are properly namespaced. The one generic name in
scope, `operations.budget.line` (`shared/budgets/models/operations_budget_line.py:11`),
is a deliberate design choice — it's meant to be shared/industry-agnostic
across future bridge modules — and doesn't collide with Odoo core. Same
trade-off the freight-side roadmap already accepted and deferred (see its
"Deliberately not doing" section). No action.

### 1.4 Manifest hygiene

All four manifests correctly set `author: "Elewa Company Limited"`,
`website: "https://www.elewa.ke"`, `license: 'LGPL-3'`, and the Odoo 19
five-part version scheme. No scaffold defaults anywhere.

Minor nits:
- `shared/budgets/__manifest__.py` has no `description` key (only `summary`) —
  the other three modules have both.
- Trailing whitespace after `'LGPL-3' ` in `shared/budgets/__manifest__.py:17`.
- Five commented-out manifest entries in `trading/__manifest__.py` (`:32,40`
  explained by an inline comment as intentional bridge-module design; `:44-53`
  — commented `demo`/`assets`/`post_init_hook` — look like leftover scaffolding
  never cleaned up).

**Action:** add the missing `description`, fix the whitespace, and either
restore or delete the five commented manifest entries (delete the scaffolding
three, keep or turn into a code comment the two that document real design
intent).

### 1.5 i18n

Every `raise ValidationError(...)` across all four modules (10 sites) is
already correctly wrapped in `_()`, including the `%`-formatted ones — this
part is solid, unlike the freight side's original state.

The real gap is chatter/activity messages that bypass `_()` with f-strings:

- `trading/models/sale_order.py:69-73, 115-119` — `note=f"""..."""` on
  scheduled activities
- `trading/models/sale_order.py:131-134` — `message_post(body=f"""Error
  creating trade: {str(e)} ...""")` — also dumps a raw exception into
  user-facing chatter
- `trading/models/purchase_order.py:110-113, 175-178` — same `note=f"""..."""`
  pattern

**Action:** wrap these 5 sites in `_()` with `%`-formatting, matching the
convention already used correctly elsewhere in these modules. Small, contained
fix — half a day.

Separately, ~90 `_logger.*` calls carry emoji prefixes (heaviest in
`account_move_trade_pnl.py` and `account_move_lifecycle.py`). Not an i18n
issue — these are developer-facing logs — but worth a cleanup pass for
professionalism/consistency. Low priority, bundle into §1.7.

### 1.6 Security model — the biggest gap, same shape as the freight side's D4

- Every `ir.model.access.csv` row in scope (`trading`: 3 rows, `trading_budget`:
  1 row, `shared/budgets`: 1 row) grants `base.group_user` — full CRUD
  including unlink — with no differentiated tiers.
- `shared/budgets_hr_expense` has no `security/` directory at all (it only
  extends existing models, so this may be acceptable, but is worth confirming
  deliberately rather than by omission).
- **Zero `ir.rule` records anywhere.** No record rules, no company/ownership
  isolation. Any internal user can read, write, or delete any trade, budget, or
  budget line system-wide.

This mirrors the freight-side roadmap's D4 exactly (what groups should exist —
Budget User / Budget Manager / read-only Controller? — and whether per-company
record rules are needed). Given trading is a single-tenant module today, the
per-company question may be moot, but the group/tier question isn't.

**Decision needed (see §2):** what groups should exist for trading and budget
approval, analogous to the freight side's D4.

### 1.7 Tests — inverted against risk

| Module | Test files | Coverage |
|---|---|---|
| `trading` | **none** | 0% — including 272 lines of branching P&L reconciliation logic in `account_move_trade_pnl.py`, entirely untested |
| `trading_budget` | `tests/test_trading_margin.py`, 5 tests | Margin/target-price computes only — no coverage of the budget lifecycle state machine or the `hr_expense` sync bridge |
| `shared/budgets` | `tests/test_operations_budget_line.py`, 16 tests | Good breadth: validation, variance, currency passthrough, chatter tracking |
| `shared/budgets_hr_expense` | `tests/test_operations_budget_line.py`, 7 tests | Reasonable coverage of its one integration point |

This is the same inversion the freight-side roadmap flagged before its Phase 2
work (untested code concentrated exactly where the money is). `trading` is the
priority: it's the largest module and has no tests at all.

**Action, in order of financial risk:**
1. `account_move_trade_pnl.py` — P&L reconciliation logic (272 lines, currently 0 tests)
2. `trading_trade.py` core CRUD and state transitions
3. `sale_order.py` / `purchase_order.py` trade-sync logic (the auto-create/update-on-confirm paths)
4. `stock.py` lot-linking
5. `trading_trade_budget.py` state machine and the `hr_expense.py` sync bridge in `trading_budget`

### 1.8 Code quality floor

- **Inline `style="..."` in views** — heavy duplication of a hand-rolled "KPI
  card" style system, concentrated in `trading/views/trading_trade_views.xml`
  (30+ occurrences, hard-coded hex colours) and
  `trading_budget/views/trading_trade_budget_views.xml` (20+ occurrences).
  Should move to SCSS classes — same fix the freight-side roadmap already
  applies to its own inline-CSS problem (§1.9 of that plan).
- **Inconsistent XML declaration headers** — present in some view files,
  missing in others (`product_template.xml`, `stock_views.xml`,
  `trading_trade_views.xml`, `trading_budget/views/menu.xml`, and its
  `trading_trade_views.xml`). Not functionally breaking; a one-pass fix.
- **Broad `except Exception`** at 5 sites (`sale_order.py:130`,
  `purchase_order.py:188`, `stock_picking.py:71,110`,
  `budgets_hr_expense/models/operations_budget_line.py:152`) — all
  catch-log-continue with no re-raise. Narrow to the specific exceptions
  actually expected.
- **Inconsistent import ordering** (`import logging` before vs. after
  `from odoo import ...`) across ~20 files. Cosmetic; fix opportunistically or
  via a `pre-commit` hook rather than a dedicated pass.
- **Committed build artifacts** — `.DS_Store` files under `trading/` and
  `__pycache__/*.pyc` under both `shared/budgets` and
  `shared/budgets_hr_expense`. Add to `.gitignore` and `git rm --cached`.

### 1.9 Module inner layout

| Module | tests/ | wizard/ | report/ | icon.png |
|---|---|---|---|---|
| `trading` | missing | missing | missing | present |
| `trading_budget` | present | missing | missing | **missing** |
| `shared/budgets` | present | missing | missing | missing (library module, may not need one) |
| `shared/budgets_hr_expense` | present | missing | missing | missing (library module, may not need one) |

No wizards or QWeb/PDF reports exist in this feature set today — likely fine
given current scope, not a gap to manufacture work against. `trading_budget`
missing its icon is the one concrete, low-cost fix (it's an installable
application-facing bridge, unlike the two `shared/` library modules).

---

## 2. Decision needed from you

**D1 — Security groups.** What groups should exist for trading and budgets —
e.g. Trader / Trading Manager, Budget User / Budget Manager, a read-only
Controller role? Same question the freight-side roadmap already asks as its
D4; answering it once probably answers both, since the shape (approval
workflow with a management tier) is the same on both verticals.

Everything else in this plan (naming, i18n, tests, quality floor) needs no
decision and can proceed in any order.

---

## 3. Phased plan

### Phase A — Mechanical fixes (small, no decisions needed)

1. Split `trading_futures.py` into one file per model.
2. Rename `trading_budget/models/trading_trade.py` → `trading_trade_budget_bridge.py`.
3. Delete the stale commented import in `trading/models/__init__.py:16`.
4. Manifest hygiene: add `description` to `shared/budgets`, fix whitespace,
   resolve the five commented-out entries in `trading/__manifest__.py`.
5. Wrap the 5 f-string chatter/note sites in `_()`.
6. Add `trading_budget/static/description/icon.png`.
7. Remove committed `.DS_Store` / `__pycache__` files; extend `.gitignore`.

### Phase B — Code quality floor (small–medium)

8. Move inline `style="..."` KPI-card CSS out of
   `trading_trade_views.xml` / `trading_trade_budget_views.xml` into SCSS classes.
9. Add missing XML declaration headers for consistency.
10. Narrow the 5 `except Exception` sites to specific exceptions.
11. Normalize import ordering (stdlib before `from odoo import ...`) — bundle
    into a `pre-commit` hook if/when one exists for this repo, rather than a
    standalone pass.

### Phase C — Tests (medium–large, no decisions needed, do this regardless of D1)

12. `account_move_trade_pnl.py` P&L reconciliation tests (highest financial risk, currently 0 tests).
13. `trading_trade.py` core CRUD / state transition tests.
14. `sale_order.py` / `purchase_order.py` trade-sync tests.
15. `stock.py` (now `stock_picking.py`) lot-linking tests.
16. `trading_trade_budget.py` state machine + `hr_expense.py` sync bridge tests.

### Phase D — Security model (needs D1)

17. Define groups per D1; replace blanket `base.group_user` ACLs with
    per-group rows across all four modules' `ir.model.access.csv`.
18. Add `ir.rule` record rules if D1 calls for per-user or per-company
    row-level restriction (may not be needed if trading stays single-tenant —
    confirm as part of D1).
19. Add a `security/` directory to `shared/budgets_hr_expense` if D1's answer
    implies it needs its own access rows rather than relying on the models it extends.

---

## 4. How progress is measured

Same bar the freight-side roadmap set for itself (§6 of
`docs/ARCHITECTURE_ROADMAP.md`), scoped to these four modules:

1. No Python-MRO mixins reappear (already true; keep it true).
2. Every model file defines exactly one model.
3. Every user-facing string (chatter, notes, errors) is wrapped in `_()`.
4. `trading`'s test suite exists and covers at minimum the P&L reconciliation
   and trade-sync paths.
5. No `ir.model.access.csv` row in scope grants blanket `base.group_user` CRUD
   without a corresponding decision recorded against D1.
