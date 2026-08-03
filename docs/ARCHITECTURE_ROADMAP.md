# Architecture Roadmap: from client projects to sellable products

Status: proposal for review. Nothing here is implemented.

This plan is written against the state of the repository after the
`budgets` decoupling and the `omni_ops` split. Every claim below was verified
against the code or a live Odoo 19 instance; where something is a judgement
call rather than a fact, it says so.

---

## 1. Where we actually are

**The layering is sound.** Dependency direction is acyclic, `shared/` never
depends on a vertical, and budgeting is genuinely optional for both verticals.
That part does not need rework.

**Four modules already depend on nothing custom** — this is the seed of a
portfolio:

| Module | LOC | Custom deps | Odoo deps |
|---|---|---|---|
| `omni_bank_reconcile` | 344 | none | `account` |
| `omni_ap_validation` | 536 | none | `account`, `hr_expense` |
| `budgets` | 419 | none | `base`, `mail`, `account` |
| `quotation` | 8,017 | none | `base`, `sale`, `contacts`, `sale_management`, `hr`, `mrp` |

**`operations` is a phantom dependency *and* is mis-filed.** `trading` and
`omni_ops` both declare it, but nothing in the repository references its three
models (`industry.type`, `workflow.stage`, and a fully commented-out
`generic.operation`) or any of its 14 `res.config.settings` fields. Its only
external contribution is one CSS file used by `omni_budget`. That is a 1,201-LOC
dependency — 439 lines of it dead code — carried by both verticals for a
stylesheet.

Worse, it does not belong in `shared/` at all: `models/config_settings.py:198`
installs the literal module names `'quotation'` and `'trading'` from settings
checkboxes. The supposedly client-agnostic layer reaches straight back into both
clients' verticals. **I put it in `shared/` during the restructure and that was
wrong.** Dropping the dead edge from `trading` also makes `trading` core-only.

**Testing is inverted against risk.** ~17,000 LOC, of which roughly 90% has no
tests, concentrated exactly where the money is:

| Module | LOC | Test files |
|---|---|---|
| `quotation` | 8,017 | 0 |
| `trading` | 2,473 | 0 |
| `omni_ops` | 2,215 | 1 (config only) |
| `omni_budget` | 1,120 | 0 — margin and cost maths |
| `operations` | 1,201 | 0 |
| `omni_ap_validation` | 536 | 0 — payment approval |
| `budgets` / `budgets_hr_expense` / `omni_bank_reconcile` / `trading_budget` | 1,567 | 1 each |

**Nothing is packaged for sale.** All ten modules are `LGPL-3`. Only `trading`
has an `icon.png`. None has `static/description/index.html`. None has an
`i18n/` directory. Runtime messages needing `_()` are concentrated in
`quotation` (24 `raise`) and `omni_ap_validation` (12) — a small, tractable
number, not the hundreds a naive grep suggests.

**There is no security model.** Zero `ir.rule` records anywhere. Every ACL
grants `base.group_user` full CRUD *including unlink* on financial data. No
product can ship this way, and it matters more now that the two verticals can
share a database.

**No module ships demo data.** The only `demo/` file in the repository,
`quotation/demo/demo.xml`, is 100% commented out. An evaluator cannot try any of
these modules without manual setup — for a product you intend to sell, this is
the single largest blocker, ahead of any code concern.

**Two defects are newly reachable because the verticals can now coexist.**
`trading` and `omni_budget` both used the sequence prefix `BUD` — cosmetic, not
a functional collision (different `code` values mean independent counters),
but it rendered two unrelated budgets identically in the UI. `omni_ops` also
mutated core MRP field labels process-wide, at the Python `Field.string` level,
via `data/field_renames.xml` calling `_rename_field_descriptions()` on install
— which would have relabeled `mrp.bom.type`/`product_tmpl_id`/`ready_to_produce`
for every other MRP app on the same instance, not just omni_ops's own screens.
**Both fixed** — see Phase 1, item 4.

**Nothing enforces any of it.** No CI. Every invariant holds because it was
checked by hand.

---

## 2. Decisions needed from you before work starts

These are not engineering choices and they gate real work. Guessing them wastes
effort.

**D1 — Licence model.** Everything is `LGPL-3` today, which permits buyers to
redistribute freely; Odoo's own store requires `OPL-1` for *paid* apps. Selling
proprietary means relicensing, which needs the agreement of anyone who has
contributed. This is a commercial/legal decision, not mine to make, and it
gates all packaging work (§4, Phase 3). *I am not giving legal advice — flag it
to whoever handles your contracts.*

**D2 — Which products go to market, in what order.** My recommendation in §3,
but it is a business call.

**D3 — The second freight client's service breakdown.** This single answer
determines whether the freight taxonomy work is a 3-day job or a 3-5 week one
(§4, Phase 5). Do they have *different names for three legs*, or a *different
number of legs*? Do not start that refactor before you know.

**D4 — Security roles.** What groups should exist (Budget User / Budget Manager?
read-only Controller?), and do you need per-company record rules so two clients
in one database cannot see each other's data?

---

## 3. The product portfolio

### Tier 1 — genuinely sellable, small, near-ready

**Bank Reconciliation Match Quality** (`omni_bank_reconcile`, 344 LOC, tested).
Depends on `account` alone. Flags statement lines as perfect/partial matches.
Useful to *any* Odoo accounting user, in any industry, on any chart of accounts —
its account codes and keyword lists are already per-company settings. **This is
the best first product**: smallest surface, already tested, already decoupled.
Blockers: `omni_` name, packaging, security groups.

**Vendor Bill Validation Workflow** (`omni_ap_validation`, 536 LOC).
Depends on `account` + `hr_expense`. A bill approval workflow with management /
operations routing. Also broadly applicable. Blockers: **zero tests**, `omni_`
name, 12 untranslated messages, packaging.

### Tier 2 — a framework, not a product

**`budgets` + `budgets_hr_expense`** (707 LOC, tested). Architecturally the
best code in the repo, but **`budgets` ships no views and no menus at all** — a
buyer would install it and see nothing. It is a developer framework. Either it
gains a generic budget UI to become sellable, or it is infrastructure that ships
*inside* the vertical products rather than being sold separately. My view: do
not try to sell it standalone; bundle it.

### Tier 3 — vertical solutions, real work remaining

**Freight Forwarding** (`quotation` + `omni_ops` + `omni_budget`, ~11,400 LOC).
The largest asset and by far the least ready. Beyond the untested 8,000 LOC and
the hardcoded three-leg taxonomy:

- **`quotation` has the client's name in 11 model `_name`s** —
  `omnifreight.route`, `omnifreight.transport.rates`, `omnifreight.margin.factor`
  and eight more. De-branding those is a full model migration, not a rename.
- **`quotation` ships the client's own market strategy as `data/`** —
  `target_data.xml` ("Target 1A: Standalone Merchants Trading In/with Africa"),
  `omnifreight_segments.xml` ("Africa Trade Expertise"). That is Omnifreight's
  commercial segmentation, not product configuration.
- It still hardcodes the `'Omnifreight Services'` category literal in search
  domains (`set_quote.py:18,40`) — the same literal already made configurable in
  `omni_ops`, left unfixed here.
- `omni_ops`' manifest describes itself as *"custom freight handling
  functionality for Omnifreight. LIS functionality is extended upon"* — naming
  both the client and their legacy system.

**Commodity Trading** (`trading` + `trading_budget`, ~3,000 LOC). Better placed
than the freight stack: its model naming (`trading.trade`, `trading.futures`) is
legitimately domain-descriptive rather than client-branded, and once the dead
`operations` edge is dropped `trading` depends only on Odoo core. One test file
covers the margin formulas. Its notable gap is i18n: **zero `_()` calls in 2,473
lines**.

### Tier 4 — deleted

**`operations` — done.** The ~30 lines of CSS it provided externally moved
into `omni_budget`, its only real consumer; the phantom dependency was dropped
from `trading` and `omni_ops` (`trading` is now core-only); and the module
itself — including the 439 lines of commented-out `generic.operation` and the
hardcoded 10-value industry Selection and English workflow-stage names it
carried — was deleted outright rather than relocated, per the recommendation
below.

It was installed (with zero configured data) in two local scratch databases;
confirmed with the project owner before deleting that those were disposable.

---

## 4. Phased plan

Phases are ordered by dependency, not by appeal. Phase 1 protects everything
after it.

### Phase 1 — Make the architecture self-enforcing (small, no decisions needed)

1. ~~**Finish and prove `tools/verify_boundaries.sh`.**~~ — **done.** The
   negative assertion (forbidden modules must stay absent) is implemented and
   was proven to actually fire: deliberately added an `omni_ops` dependency to
   `ele_bank_reconcile` and confirmed the check caught it, before reverting.
2. ~~**Wire it into CI**~~ — **done and confirmed green.**
   `.github/workflows/verify-boundaries.yml` runs the script on every push and
   pull request, against a real `postgres:15` service container and a fresh
   Odoo 19 checkout. The connection is env-var-based (`PGHOST`/`PGUSER`/
   `PGPASSWORD`), which is standard libpq behaviour and needed no changes to
   the script itself.

   The first run caught a real bug immediately: `ODOO_PYTHON=python` (a bare
   command name, since CI has no venv to point at) failed the script's own
   `[ -x "$PYTHON" ]` check, because that test only checks a literal path and
   does not do a `$PATH` lookup. Fixed by resolving `PYTHON` through
   `command -v` first. The second run passed on GitHub's actual
   infrastructure — the exact kind of bug, and the exact speed of catching it,
   this job exists for.

   Not yet done: a real Odoo test suite only runs per-module when invoked
   directly (`--test-tags=/<module>`), not as part of this boundary check for
   every module — `omni_budget` and `ele_ap_validation` still have none to run
   regardless (see item 5/6 below). Wiring in whatever suites exist as a
   separate CI step is a small follow-up, not a blocker.
3. ~~**Kill the phantom `operations` dependency**~~ — **done.** (Tier 4 above.)
   Verified against a real Odoo instance: `omni_ops`, `omni_budget` and
   `trading` all install and `omni_ops`'s suite passes 10/10 with `operations`
   left uninstalled, and the budget list's CSS decoration resolves from its
   new home in `omni_budget`.
4. **Fix the two coexistence defects** that the verticals-in-one-database change
   made reachable:
   - ~~the duplicate `BUD` sequence prefix~~ — **done.** Correction to how this
     was originally described: the two sequences use different `code` values
     (`trading.budget` vs `omni.mrp.budget`), so they were always independent
     counters — there was no functional/database collision, only a cosmetic
     one, where a shared "BUD" prefix rendered two unrelated budgets
     identically in the UI. Fixed by giving each vertical a distinct prefix
     (`TRD/BUD/`, `FRT/BUD/`). While there, also fixed a real ownership bug
     found along the way: the trading-side sequence lived in core `trading`'s
     data files even though only the optional `trading_budget` bridge ever
     consumes it — moved to `trading_budget`, mirroring how `omni_budget` owns
     its own sequence. Verified: installing both verticals together renders
     each budget under its own distinct prefix, and `trading_budget`'s suite
     still passes 5/5.
   - ~~`omni_ops/data/field_renames.xml` rewriting core MRP labels
     process-wide~~ — **done.** Deleted the data file, its manifest entry, and
     the `_rename_field_descriptions()` method that mutated `mrp.bom`'s field
     objects at the Python level on every install. It turned out to be pure
     dead weight: every rename it performed was already duplicated by scoped,
     correctly-inherited view overrides that already exist in this repo
     (`title_overrides.xml`'s tree-view rename, `rename_views.xml`'s form-view
     rename) — the global version added nothing for `omni_ops`'s own screens
     and only risked corrupting every other app's view of the same fields.
     Verified: `omni_ops` installs and passes 10/10 without it, and the form
     view still renders "Process Type" / "Service" for `type` /
     `product_tmpl_id` via the scoped override, confirmed through Odoo's own
     view-composition (`get_view()`), not just by reading the XML.

Phase 1 is now complete.

### Phase 2 — Close the test and correctness gap (medium, no decisions needed)

5. **Fix the `fob_lod` bug.** `fob_lod` is a valid `service_scope` value with no
   branch in the decode ladder at `omni_ops/models/omni_mrp_production.py:82`,
   so a FOB + Destination file falls to `else` and reports *no services*,
   silently zeroing that budget's charged amounts and margin. Independent of any
   taxonomy decision. Cheap.
6. **Tests for `omni_budget`** — the margin and cost computations. Highest
   financial consequence of any untested code.
7. **Tests for `omni_ap_validation`** — the approval state machine, the
   expense-raising path, and the `action_post` override that suppresses Odoo's
   payment generation.
8. **Deduplicate the two currency-conversion mixins.** `omni_budget` and
   `quotation` each have one, with *divergent error contracts* — one logs and
   returns the unconverted amount, the other raises. Same operation, two
   behaviours, on money.

*Risk: low-medium. (4) and (7) change behaviour and need care.*

### Phase 3 — Product hardening (needs D1, D4)

9. **Security model** (D4): groups, ACLs per group instead of blanket
   `base.group_user` CRUD, and record rules for company isolation.
10. **Wrap runtime messages in `_()`** — 29 `raise` and 13 `body=` sites — and
   generate `.pot` files.
11. **Relicense** per D1, adding the licence header convention.
12. ~~**De-brand the two Tier-1 modules**~~ — **done.** `omni_bank_reconcile` →
    `ele_bank_reconcile` and `omni_ap_validation` → `ele_ap_validation` (the
    `ele_` vendor prefix, not the `ap_validation`/`bank_reconcile` names
    originally proposed here), along with every `omni_*` field, method and
    relation table inside each. Neither was installed anywhere, so no rename
    migration was needed — the risk this item warned about did not apply yet.
    It will apply to any *future* rename, once either module has a real
    install base.

    This repository already contains a cautionary precedent. `quotation` was
    evidently once called `omni_quotation`, and the rename was never finished —
    `quotation/models/port.py:55` still calls
    `self.env.ref('omni_quotation.action_omnifreight_route')` for a record that
    now lives at `quotation.action_omnifreight_route`, so that button is broken.
    Worth fixing on its own, and worth treating as evidence that renames here
    need a checklist rather than a find-and-replace.
13. **Demo data for every product.** Currently zero modules ship any. This is
    the top resale blocker and it is independent of all the code work — an
    evaluator who installs and sees an empty screen does not buy.
14. **Packaging**: `icon.png` and `static/description/index.html` per product.

*Risk: (11) is the riskiest item in the plan — module renames touch every XML ID.
Do it while the install base is still zero.*

### Phase 4 — Vertical hardening

15. Tests for `trading` and for `omni_ops`' business logic (it has 2,215 LOC and
    one config test file).
16. **Decide `quotation`'s fate — this is the pivotal call for the freight
    product.** 8,017 LOC, no tests, no README, 11 client-branded model names,
    client marketing data in `data/`, and its own service taxonomy inconsistent
    with `omni_ops`'. It is 47% of the codebase. Three honest options:
    - *Invest*: de-brand 11 models with migrations, strip the client data, add
      tests. Weeks of work on code nobody has tested.
    - *Scope out*: sell Freight Forwarding as `omni_ops` + `omni_budget` only,
      and treat quotation as bespoke client work. Requires severing the
      `omni_ops` → `quotation` dependency, including the `getattr` reads of
      `fob_total_cost_est` and friends.
    - *Rewrite the needed slice*: keep the client's instance as-is, build a
      smaller quotation module for the product.

    I would not attempt to sell the freight vertical without resolving this.
17. File and model naming cleanup (`omni_*.py` files not named after their
    models; `operations.budget.line` living in `budgets`). Mechanical, wide,
    zero functional gain — last.

### Phase 5 — The freight taxonomy (needs D3; do not start speculatively)

The `fob`/`freight`/`lod` triad is the concrete ceiling on onboarding a second
freight client. Verified scope: **39 files, ~505 references, 133 in XML**.
`budget_cost_computation_mixin.py` alone has 96 of its 307 lines referencing it.

`service_scope` is a **bitmask encoded as a Selection** — its 7 values are
exactly 2³−1, every non-empty subset of three legs. It does not generalise: four
legs would need 15 values and 16 decode branches. Around 30 `{fob,freight,lod}_*`
field triples across `omni_budget` and `omni_ops` hardcode the cardinality.

Worse, **`quotation` has a parallel, inconsistent taxonomy**: a 6-value
`quote_type` (`fob_only`, `freight_only`, `lod_only`, `freight_dap`, …) of which
only two values overlap with `service_scope`, plus cost fields where two legs are
prefixed (`fob_total_cost_est`, `lod_total_cost_est`) and the third is not
(`total_cost_est`). `omni_budget` reads those by name via `getattr`, so this
**cannot be contained** to `omni_ops`/`omni_budget`.

**Recommendation: do nothing here until D3 is answered.**
- If the difference is *naming only* → a `selection=` callable plus label config,
  ~3-5 days.
- If the difference is *cardinality* → only a real `service.type` model with a
  Many2many scope works. Stage it: (i) replace the four `service_type`
  Selections and the `service_scope` bitmask, killing the 2^N problem and the
  `fob_lod` bug (~10 files, contained); (ii) collapse the budget field triples
  into a child model and regenerate the budget views (~20 files); (iii)
  reconcile `quotation`. Estimate 3-5 weeks across ~40 files.

Refactoring this before knowing which case you are in risks doing the expensive
version of a cheap problem.

---

## 5. Deliberately not doing

- **Splitting `operations.budget.line` into per-vertical models.** Textbook
  advice would make it an `AbstractModel` mixin so each vertical gets its own
  table, eliminating the shared field namespace and the required-field bleed.
  But `hr.expense.budget_line_id` is a `Many2one` to the concrete model, and a
  Many2one cannot target a mixin — you would need a `Reference` field (losing
  FK integrity and domain filtering) or a per-vertical bridge for every
  actualization backend. Since each client runs their own database, the shared
  table costs almost nothing in practice. **Keep it**, and treat the
  test-isolation rule as inherent rather than a wart.
- **Renaming `operations.budget.line`** to match the module it lives in. Correct
  but expensive (core model, every XML ID, the table). Revisit only if the
  naming drift causes a second real bug.
- **Speculative taxonomy work.** See Phase 5.

---

## 6. How progress is measured

Not by items ticked, but by these being continuously true in CI:

1. Every `shared/` module installs on a database with **no vertical present** —
   and pulls none in.
2. `omni_ops` installs with **no budgeting present**.
3. Both verticals install in **one** database.
4. Every module's test suite passes in the isolation it requires.
5. No module regains a dependency on `operations`.
6. No module in `shared/` references a vertical module by name.

Invariants 1-3 are claims the layout makes about reusability. If they are not
enforced, they will quietly stop being true — which is precisely how this
codebase reached the state it was in. Invariant 6 exists because `operations`
violated it while sitting in `shared/`, and nothing noticed.

---

## 7. What I would do first

If you want one thing: **take `ele_bank_reconcile` all the way to a shippable
product.** It is 344 LOC, already tested, already decoupled, already
configurable, depends on `account` alone, and (as of this rename) already
carries its final name. Walking it through security → i18n → demo data →
packaging proves the whole pipeline and gives you a template. Doing that once
is worth more than partial progress on all ten.
