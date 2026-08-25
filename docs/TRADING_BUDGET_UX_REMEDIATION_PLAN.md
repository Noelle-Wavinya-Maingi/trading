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

## Phase 6: Findings from a live walkthrough (2026-08-25)

Confirmed by running the app against a real trade record (TRD/LONG/00001,
product Cocoa), not just reading the code. Two items are dev-environment
cleanup rather than product bugs; the rest are real, reproducible defects.

13. **Duplicate "Missing required fields" toasts stack instead of replacing**
    - Interacting with the trade form (switching tabs, scrolling) re-triggers
      validation and stacks a new identical toast on top of the previous one
      rather than deduplicating or updating it in place. Reproduced with two
      and then three identical toasts visible at once on the same field.
    - Fix: the notification service should dedupe by message content/field,
      or clear the previous toast before showing a new one for the same
      validation error.

14. **`ele_trade_type` has existing rows with a null value despite being
    effectively required**
    - Schema warnings on every module load/update: `Missing not-null
      constraint on trading.trade.ele_trade_type` and `...trading.trade.budget.ele_trade_id`.
      In the UI this surfaces as a required "Trade Type" field rendered
      empty and in red on an existing, previously-saved trade record.
    - This points to a field added after existing data was created, with no
      backfill migration. Needs a data migration script, not just a UI fix.

15. **Open Positions vs. Closed Positions cards break their own visual
    pattern** (Trade Summary tab, form view)
    - Open Positions renders a clean symmetric 2×2 grid (Open Qty / Purchase
      Cost, Unrealized P&L / Market Price). Closed Positions breaks that
      rhythm: Additional Costs sits alone in a full-width row with its own
      divider line above an otherwise-equivalent 2×2 grid (Sold Qty / Sales
      Value, Realized P&L / Cost Basis) — the divider implies a sub-grouping
      that doesn't exist in the data model.
    - Proximity in the Open Positions grid doesn't match what a trader
      actually cross-references: Open Qty sits next to Purchase Cost, and
      Unrealized P&L sits next to Market Price, when Qty↔Market Price and
      Cost↔P&L are the pairs someone would actually want side by side.
    - No visual hierarchy distinguishes the headline number (Unrealized/
      Realized P&L) from supporting figures — every metric in both cards
      gets identical caption+value styling.
    - Inconsistent iconography: Closed Positions gets a checkmark icon in
      its header, Open Positions gets none, with no visible rule for which
      cards earn one.
    - Verified with a real trade (Cocoa, 100 Ton, Purchase Price $25.30,
      Market Price $30.00): Unrealized P&L correctly renders in green
      ($470.00) once there's a real signed value — the color decoration
      logic itself works as intended. The other issues above (grid
      asymmetry, proximity, hierarchy, iconography) still apply regardless.

16. **Dev-environment cleanup (not a product bug, but worth carrying
    forward as a checklist item)**
    - `trading_dev` still had the pre-rename `trading` / `trading_budget`
      modules installed, with orphaned views referencing dead field names
      (`trade_type` instead of `ele_trade_type`) that crashed the entire
      Trades screen for any user. Cleaned up in this session by uninstalling
      the orphaned modules; worth checking whether staging/other
      environments carry the same leftover from the ele_ rename migration.
    - The `.claude/launch.json` addons-path and `-u` module list were stale
      (referenced the pre-restructure folder layout and module names) and
      have been corrected.

17. **Confirming a Purchase Order links to an existing draft trade for the
    same product instead of always creating a new one**
    - Confirming a real PO (Cocoa, 100 Ton, $25.30/Ton) attached itself to
      a pre-existing draft trade (`TRD/LONG/00001`) rather than creating a
      second trade record. This may be intentional (one trade per open
      position per product) or may silently merge two unrelated purchases
      into the same trade depending on the matching logic in
      `ele_purchase_id` / trade lookup. Worth an explicit product/business
      confirmation of the intended matching rule, since it's not stated
      anywhere in the UI when it happens.

## Phase 7: Why this matters in plain terms

The items above are written for someone picking up the code. This section
is the same set of concerns translated into what actually happens to a
person using the app day to day — for anyone reading this plan who isn't
going to touch the code directly.

**The short version:** the app isn't doing the wrong math. It's not
explaining itself as the user goes. Handed to a new trader or finance
hire with no training, they would get stuck or make a real mistake within
their first ten minutes, and not because any calculation is broken.

18. **There's no obvious way to create a trade the "right" way**
    - A new user will naturally click "New" on the Trades screen and hit a
      confusing empty form with a required field left blank. The actual
      intended path is to confirm a normal Purchase or Sale Order, which
      creates the trade automatically. Nothing on screen tells them that.
      So they either give up, or hand-fill a form that was never meant to
      be filled by hand.

19. **Errors talk to a programmer, not to the person using the app**
    - We personally hit `KeyError`, `RPC_ERROR`, raw Python tracebacks, and
      an `OwlError` stack trace inside an "Oops!" dialog. A trader has no
      path forward from that beyond "contact your administrator" — no
      plain sentence explaining what broke, and no indication of who to
      actually contact. A small hiccup ends up reading as "the whole
      system is broken."
    - Access-denied errors have the same problem: "contact your
      administrator" with no link, no request button, and no named
      admin — for a small team this becomes a hallway conversation
      instead of something the app helps resolve itself.

20. **The app quietly does things without telling the user**
    - Confirming a Purchase Order can silently attach it to an *existing*
      trade rather than creating a new one (see item 17) — a trader has
      no way to know, without digging, whether they just opened a new
      position or added to one that already existed. This is exactly the
      kind of invisible side effect that causes a real financial mix-up,
      not just an annoyance.

21. **Too much visual noise for the common case**
    - Every trade shows four separate currency fields (Currency, Purchase
      Currency, Sale Currency, Market Price Currency), all defaulting to
      USD. For the common single-currency trade, that's four fields a
      user has to visually confirm are all correct, for a distinction
      that only matters for a minority of cross-currency trades.
    - Computed figures (Open Qty, Purchase Cost, Market Price, P&L, etc.)
      render identically whether the user set them or the system
      calculated them — there's no visual cue for "this one you can
      correct" versus "this one will just be overwritten."

22. **First run gives no guidance**
    - A brand-new installation shows an empty Trades board (Draft /
      Confirmed / Closed columns, nothing in them) with no pointer to
      "start by confirming a Purchase or Sale Order." Anyone starting
      cold has to already know the intended workflow.

## Phase 8: Engineering discipline gaps (repo-wide, not Trading/Budget-specific)

Unlike Phases 1-7, this phase isn't about the Trading/Budget UI — it's about
two process gaps in how this repo evolves its own schema and proves its own
fixes, both of which caused real breakage during this remediation work (not
hypothetical risk). Scope is the whole repo, since both gaps are structural,
not vertical-specific.

23. **No migration story for schema changes**
    - Two real breakages happened in this session with no accompanying
      migration script: `ele_win_rate`'s Float -> Boolean change (Phase 1)
      broke an existing database with a Postgres cast error
      (`cannot cast type double precision to boolean`), and the
      `trading`/`trading_budget` -> `ele_trading`/`ele_trading_budget`
      module rename left orphaned views/data under the old names in an
      existing dev database, crashing the Trades screen for any user until
      manually cleaned up.
    - Action items:
      - Write a migration convention doc (e.g. `docs/MIGRATIONS.md`)
        describing when a field rename/retype/removal or a module rename
        requires a migration script, and where it lives — Odoo's own
        `migrations/<version>/pre-*.py` / `post-*.py` convention already
        exists for exactly this and isn't used anywhere in this repo yet.
      - Backfill the two migrations this session actually needed:
        a pre-migrate script converting `ele_win_rate`'s existing float
        values to boolean explicitly (not relying on Postgres's implicit
        cast), and a documented cleanup path (or an OpenUpgrade-style
        module-rename registration) for databases still carrying the old
        `trading`/`trading_budget` module names.
      - Add a CI check that fails when a field's type changes without a
        corresponding migration script touching that field name.

24. **Test coverage that doesn't actually catch regressions**
    - Two real regressions in Phase 2 (an `hr.expense` re-sync crashing on
      a `done` budget line, and short trades never auto-closing) were only
      caught because a reviewer manually reproduced them against a live
      database — the existing test suite passed green on both bugs.
      "Tests pass" in this repo does not yet reliably mean "no regression."
    - Action items:
      - Audit both regressions and add tests named for the scenario they
        guard against (not just "test passes now"), so the next reader
        sees what bug class each test exists to catch.
      - Adopt a rule: a behavior-changing PR doesn't merge without a test
        that would have failed before the fix — prove the test would have
        caught the bug, not just that a test was added.
      - Add a short "did I reproduce this live" checklist item to the PR
        template specifically for changes touching a compute method or a
        workflow state transition, since both slipped-through regressions
        were exactly that shape.

## Notes

- File/line references are accurate as of 2026-08-20 (2026-08-25 for Phases 6-8)
  and will drift as the codebase changes; re-verify before starting each item.
- This is a static-analysis-based plan; validate priorities against real user
  feedback (trader/finance) before committing engineering time to Phases 3-5.
- Phase 8 is repo-wide engineering process, not Trading/Budget UI-specific;
  track it as its own follow-up rather than blocking the UI phases on it.
- No code has been changed as part of producing this plan.
