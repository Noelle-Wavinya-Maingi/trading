# Testing Discipline

## Why this document exists

Commit `0308080` ("Phase 2: gate budget-line edits and consolidate trade
closure") fixed two bugs that had both shipped with a fully green test suite:

1. **`operations.budget.line` done-lock vs. backend re-sync.** Locking
   `actual_amount` once a line is `done` is correct, but
   `budgets_hr_expense`'s own resync path (an expense correction pushing its
   new amount back onto the line) needs to bypass that lock. An early,
   value-based exemption ("only exempt while `actual_amount` is falsy") only
   covered the very first backfill — a second correction on an
   already-nonzero line hit the lock and raised `ValidationError`. Nothing in
   the test suite exercised a *second* correction after `done`, so this
   never surfaced until it hit production-shaped usage.
2. **Short-trade closure on the create path.** `sale.order.action_confirm()`
   used to run its own inline "is this trade fully sold" check, but only on
   the *update* path (an order already linked to a trade before confirm).
   The *create* path — a brand-new order that auto-creates and fully sells a
   short-tradeable line in the same `action_confirm()` call — never ran that
   check, so a fully-sold short trade with no purchase leg was left sitting
   in `confirmed` instead of closing. The existing test for this scenario
   only exercised the update path; the create path had no test at all.

Both bugs are examples of the same failure mode: **a green test suite proves
the tests that exist pass, not that the behavior a change actually needs is
covered.** This is especially easy to miss for two categories of code that
otherwise look like anything else:

- **Compute methods**, where a bug is a wrong or stale value rather than an
  exception — nothing crashes, so nothing fails unless a test specifically
  asserts on the value.
- **Workflow state transitions**, where a bug is a state that silently fails
  to change (a trade that should close but doesn't) rather than an error —
  same problem, the absence of a state change doesn't raise anything on its
  own.

Both of Phase 2's bugs were exactly this shape. "Tests are green" was never
evidence that either code path was regression-free; it was only evidence
that whatever narrower scenario the existing tests happened to cover was
regression-free.

## The rule

**A behaviour-changing PR must include a test that is proven to have failed
against the pre-fix code, not just a test that was added alongside the fix
and is now green.** A test written after the fix, against the fixed code,
can pass for the wrong reason (e.g. asserting something the fix didn't
actually change) and nobody would notice. Running it against the pre-fix
code is what confirms it is actually exercising the bug.

This is enforced at PR time via the checklist in
[`.github/pull_request_template.md`](../.github/pull_request_template.md).

## What "proven to fail" means operationally

Check out (or reconstruct, per the notes below) the pre-fix state of the
specific model file(s) the fix touches, run the new/updated test against it
in an isolated throwaway database matching this repo's own test-isolation
rules (see each module's README, and the isolation table in the repository
root `README.md`), and record the actual failure output. A worktree checked
out at the parent of the fix commit is the cleanest way to do this without
disturbing your working branch:

```bash
git worktree add /tmp/prefix-check <fix-commit>^
```

then point `--addons-path` at the worktree instead of the main checkout and
run the target test(s) alone (`--test-tags=/<module>:<TestClass>.<method>`
where the runner supports it, or filter by class/module and read the
per-test log lines).

### Regression proof for commit `0308080`

Both fixes above were verified this way, in a worktree at `0308080^`
against a throwaway PostgreSQL database, `--addons-path` pointed at the
worktree's copies of `shared/`, `product/commodity_trading/`, etc.

**`test_new_order_fully_selling_a_short_line_creates_and_closes_trade_in_one_confirm`**
(create-path short-trade closure) fails on the unmodified pre-fix code with
no changes needed beyond copying the test itself into the worktree:

```
odoo-bin -d <throwaway> --addons-path=<odoo>/addons,<worktree>/shared,...,<worktree>/product/commodity_trading,... \
  -i ele_trading --test-enable --test-tags=/ele_trading:TestSaleOrderTradeSync --stop-after-init
```

```
FAIL: TestSaleOrderTradeSync.test_new_order_fully_selling_a_short_line_creates_and_closes_trade_in_one_confirm
AssertionError: 'confirmed' != 'closed'
```

The pre-existing sibling test in the same commit
(`test_confirming_order_with_tradeable_line_creates_a_short_trade`, whose
expected status the same commit updated from `'confirmed'` to `'closed'`)
fails the same way on the same pre-fix run, confirming this is the create
path specifically, not a fixture problem.

**`test_short_trade_with_no_purchase_leg_closes_once_fully_sold`**
(update-path short-trade closure) does *not* fail against the literal
parent commit, because pre-fix `sale_order.py` still had its own inline
"sold quantity >= trade.quantity" check on the update path — the bug this
test guards against is specific to a *naive* version of the centralization
refactor (routing every caller through one `_auto_close_if_fully_matched()`
that only checks `ele_is_fully_matched`, i.e. the long-trade condition, and
drops the short-position branch). Reconstructing that intermediate state —
`_auto_close_if_fully_matched()` without its
`_is_short_position_fully_sold()` branch — and rerunning the test does
reproduce the failure (`AssertionError: trade.ele_status != 'closed'`). This
test is retained under its bug-stating name because it is exactly the
regression the centralization would otherwise reintroduce; its rename from
`test_trade_closes_once_fully_sold` documents that shift in what it's
proving.

**`test_expense_amount_correction_resyncs_after_line_is_done`**
(done-lock vs. backend resync) does not fail against the literal parent
commit either, since the done-lock did not exist there at all — the bug and
its fix landed in the same commit. Reconstructing the *naive* value-based
exemption described in that commit's message
(`if not line.actual_amount: continue`, no `budget_line_backend_sync`
context flag) and rerunning the test against it reproduces the failure:

```
ERROR: TestOperationsBudgetLineExpenseActualization.test_expense_amount_correction_resyncs_after_line_is_done
odoo.exceptions.ValidationError: Budget line 'Test line' is Done and can no longer be edited.
```

isolated per `shared/budgets_hr_expense/README.md`'s rule (`budgets_hr_expense`
installed alone, no client bridge module).

All three tests pass cleanly against the current (post-fix) code, run the
same way.

**Takeaway for future proofs:** when a fix and the bug it addresses land in
the same commit (no separate "buggy" commit ever existed in history),
proving failure means reconstructing the specific naive/intermediate logic
the commit message describes as having been replaced, not just checking out
the parent commit — the parent commit may predate the bug's introduction
entirely, and will pass trivially for the wrong reason if so.

## Test isolation

See the isolation table in the repository root `README.md` and each shared
module's own README (e.g. `shared/budgets_hr_expense/README.md`) for which
suites require their own throwaway database. Running a suite in the wrong
database (e.g. `budgets_hr_expense` with a client bridge module also
installed) produces failures unrelated to the code under test and is not a
substitute for the isolation described there.
