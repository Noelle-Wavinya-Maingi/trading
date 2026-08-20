# Trading & Budget Module: Remediation Plan

Source: `ECL_Trading_Budget_UX_Review_20Aug2026.docx` (product/UX review, 2026-08-20).
Branch: `review/trading-budget-ui-ux`.

This plan sequences the fixes from that review by risk to the user, not by effort.
Each item lists the concrete files/fields involved so it can be picked up as a
standalone task.

**Scope note:** Omnifreight (`custom/omnifreight/omni_budget`) is out of scope,
no changes will be made there. It is referenced below only where the
original review compared it to Trading/Budget for context; any item that
would require editing Omnifreight code has been removed or marked
accordingly.

## Phase 1: Correctness & trust (do first)

1. **Fix misleading labels**
   - `ele_total_pnl` labelled "Realized Margin" but includes unrealised P&L +
     additional revenue, see [trading_trade_budget.py:98](product/commodity_trading/ele_trading_budget/models/trading_trade_budget.py)
     (via [trading_trade_pnl.py:184](product/commodity_trading/ele_trading/models/trading_trade_pnl.py)).
     Relabel to reflect the real computation, or split into a true realised-only field.
   - `ele_win_rate` labelled "Win Rate (%)" but is a binary 0/100 flag per trade,
     see [trading_trade_pnl.py:103-108](product/commodity_trading/ele_trading/models/trading_trade_pnl.py).
     Relabel (e.g. "Profitable") or compute an actual rate across trades.

2. **Replace silent failure paths with visible warnings**
   - Currency conversion fallback swallows exceptions and shows an unconverted
     amount; confirm the exact path within `ele_trading` / `shared/budgets`
     (the original review cited a mixin also used by Omnifreight; only the
     Trading/Budget usage is in scope here).
   - Delivery-to-trade linking failures caught broadly, logged only, see
     [stock_picking.py:73,116].
   - Add a user-facing warning (banner/tooltip/ValidationError as appropriate)
     wherever a number shown to the user may be wrong as a result.

## Phase 2: Workflow integrity

3. **Wire up or remove dead workflow actions**
   - `trading.futures` `action_close_future` / `action_reopen_future` exist but
     are unreachable, statusbar not clickable, no button calls them
     ([trading_futures.py:280-304], [trading_futures_views.xml:30]).
   - Decide per action: wire it into the UI, or delete the dead code.
   - (Omnifreight's equivalent hidden-button issue is out of scope.)

4. **Make `operations.budget.line` state actually gate editing**
   - `actual_amount` is editable in every state (draft/confirmed/done);
     enforce read-only past "confirmed" or remove the state field if it's
     not meant to constrain anything.

5. **Single, explicit cause for trade closure**
   - A trade can close via the explicit action or silently via a P&L recompute
     side-effect, see [trading_trade_pnl.py:198-200]. Remove the implicit path.

## Phase 3: Terminology & onboarding

6. **Standardise terminology**
   - "Budget" vs "Target" (same fields relabelled per trade type,
     [trading_trade_budget.py:47-59] / [trading_trade_budget_views.xml:47-48,79-80]).
   - "Margin" (target-vs-actual P&L vs. "Realized Margin" within
     Trading/Budget; the review also found a third, unrelated Omnifreight
     margin calculation, but reconciling that is out of scope).
   - "Variance" (three formulas shown together on one form).
   - "Actual" (different data sources in `operations.budget.line` vs
     `trading.trade.budget`).
   - Pick one meaning per term per context; where a term must differ by trade
     type, say so on screen rather than relying on inference.

7. **Add help text to the highest-leverage fields first**
   - `ele_additional_costs` / `ele_additional_revenue`: feed every downstream
     P&L calc, currently have no `help=` at all
     ([trading_trade.py:148-156]).
   - The budgeted/target distinction on the Trade Budget form.

## Phase 4: Visual/Gestalt cleanup

Note: the review found Omnifreight had reimplemented Trading's KPI card
pattern with hardcoded inline styles instead of the shared SCSS classes. Since
Omnifreight is out of scope, no consolidation work happens on that side;
this phase only cleans up within Trading/Budget itself.

8. **Fix heading hierarchy** on the Trade Budget form: the standalone `h4`
   ("Additional Costs & Additional Revenue") renders smaller than the `h5`
   card headers above it ([trading_trade_budget_views.xml:142]).

9. **Fix inconsistent variance disclosure and ad-hoc spacing**
    - Standardise whether hidden-vs-always-shown variance fields follow one
      rule ([trading_trade_budget_views.xml:62-64, 94-96, 124-136]).
    - Replace the stray `<br/>` and mixed `o_trading_mt2` / `mt-3` usage with
      one consistent spacing utility ([trading_trade_budget_views.xml:139]).

10. **Replace hover-only tooltips** on KPI info icons with visible inline text
    where the info is decision-relevant
    ([trading_trade_views.xml:151-152, 190-192, 239-241, 245-246, 251-252]).

## Phase 5: Information architecture (longer-term)

11. **Give Budget a first-class menu/permission surface** instead of an
    injected menu item inside Trading's root menu with widened `group_ids`.

12. **Consolidate duplicated business logic within Trading/Budget**
    - Duplicate budget recording (trade-level quantity/price vs.
      `operations.budget.line` rows), with silent fallback to live quoted
      price when no lines exist ([trading_trade_budget.py:109-140]) and no
      reconciliation UI.
    - (The review also noted Omnifreight duplicates margin and currency
      conversion logic separately from Trading/Futures; since Omnifreight
      is out of scope, that duplication is left as-is; only the Trading-side
      implementation may be cleaned up.)

## Notes

- File/line references are accurate as of 2026-08-20 and will drift as the
  codebase changes; re-verify before starting each item.
- This is a static-analysis-based plan; validate priorities against real user
  feedback (trader/finance) before committing engineering time to Phases 3-5.
- No code has been changed as part of producing this plan.
