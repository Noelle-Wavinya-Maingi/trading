# Migration Plan: taking `omni_ops` off `mrp`, onto a generic process engine

Status: proposal for review. Nothing here is implemented.

This plan scopes replacing Odoo core `mrp` (manufacturing) as the engine
behind `omni_ops`'s freight-file operations, with a new generic "process
engine" (steps, sequencing, state machine — no BOM/routing/work-center
capacity planning) that both `omni_ops` and, if it ever needs staged
operations, `ele_trading` could sit on. Every claim below was verified by
reading the actual source of `omni_ops`, `omni_budget`, and `quotation`
(see the touchpoint inventory in §2) — nothing here is inferred from file
names or field counts.

---

## 1. Why this is a migration, not an extraction

Every shared piece built so far this cycle (`order_bridge`, `budget_bridge`)
was a genuine extraction: two independent implementations of the same idea
already existed, and the shared mixin pulled out exactly the part that was
identical. This is different. `omni_ops` is not "using `mrp` as a data
store" that a generic model could swap in for — it overrides two of `mrp`'s
own internal algorithms and calls a third directly:

- **`mrp.bom._bom_find`** (native BOM-resolution, called from inside core
  `mrp`/`sale`/`stock` whenever anything needs "which BOM applies to this
  product") is overridden in `omni_bom.py` to let `omni_service`-typed
  products through a filter that normally excludes them.
- **`mrp.production._compute_workorder_ids`** (native compute that explodes
  a BOM's operations into work orders via routing/work-center logic) is
  overridden in `omni_mrp_production.py`: for service BOMs it swaps in a
  wholly custom `_create_service_workorders()` that builds work orders
  directly and explicitly skips mrp's own dependency setup ("to avoid
  cyclic dependency errors" — a comment in the code, not this plan's
  characterization).
- **`quotation`'s `_bridge_create()`** (the `order_bridge` implementation
  built this cycle) calls `mo.action_confirm()` — `mrp.production`'s own
  native confirm method — directly. That single call is what triggers
  `_compute_workorder_ids` above, stock-move creation, and the state
  transition to `confirmed`. It is the one call site that has to be
  redirected to whatever the process engine's own "confirm" becomes.

There is no `super()` to fall back into once `mrp` is gone. Replacing it
means writing the BOM/template-resolution, step-generation, sequencing, and
state-machine logic that `mrp` currently provides, from scratch, at whatever
scope this plan settles on (see §4 — it does not have to mean rebuilding
work-center capacity planning or the mrp scheduling UI).

---

## 2. Full touchpoint inventory

### `omni_ops/models/omni_mrp_production.py` (`_inherit = 'mrp.production'`)
| Touchpoint | Kind |
|---|---|
| `_compute_workorder_ids` | **Algorithm override.** Branches on BOM type; service BOMs bypass mrp's routing-based generation entirely via `_create_service_workorders()`. |
| `workorder_ids`, `blocked_by_workorder_ids` | Native relations directly written to fake sequencing (`blocked_by_workorder_ids = [(4, id)]` in `_add_sequential_dependencies`) — exactly the shape the process engine's step-dependency field needs to replace natively. |
| `bom_id`, `product_id`, `product_qty`, `product_uom_id`, `sale_line_id`, `date_start`, `date_finished` | Passive reads/writes, no algorithm change. |
| `_onchange_product_id`, `create`, `write` | Passive extensions — call `super()` and add omni-specific side effects only. |
| `action_confirm`, `button_plan`, `_plan_workorders`, `action_cancel`, `_post_inventory` | **Not overridden.** Confirmation happens through `quotation`'s direct `mo.action_confirm()` call (see below) — omni_ops itself never touches these. |

### `omni_ops/models/omni_mrp_workorder.py` (`_inherit = ['mrp.workorder', 'service.state.mixin']`)
| Touchpoint | Kind |
|---|---|
| `workcenter_id` required→optional | **Constraint override** on a native field. |
| `action_start`, `action_finish` | Additive wrappers (`super()` + chatter/tracking) — do not replace mrp's state-transition logic. |
| `button_finish`, `_set_dates` | Pass-through wrappers with no added logic, but they still invoke mrp's own `button_finish` (quality checks, `qty_produced`, cascades to `mrp.production` state) and `_set_dates` (workcenter-calendar-based duration calculation) for **every** work order, including ones with no real work center. |
| `create` | Passive; resolves `workcenter_id` from `freight_service_type` before delegating. |

### `omni_ops/models/omni_mrp_workcenter.py` (`_inherit = 'mrp.routing.workcenter'`)
Entirely custom fields and a bespoke state machine (`_do_start`/`_do_done`/`_do_cancel`/`action_cycle_state`) layered on the routing/operation record. **No `super()` calls into any native mrp method** — this file doesn't override mrp behavior, it just uses `mrp.routing.workcenter` as a container for what is, in substance, already a hand-rolled "step" state machine.

### Mixins
- `omni.service.scope.mixin` (into `mrp.bom`) directly rewrites `mrp.bom`'s own native `operation_ids` One2many (`self.operation_ids = [(5,0,0)]` then rebuild) — bypassing mrp's normal BOM-operation editing flow.
- `service.state.mixin` (into `mrp.workorder`) branches on `hasattr(record, 'button_start')` and, when true, calls mrp's own `button_start`/`button_finish` as the happy path, falling back to a raw `write()` only on exception — a real, if defensive, dependency on mrp's native transition methods.
- `omni.service.template` / `omni.bom.utilities.mixin` — standalone or cosmetic; no algorithm coupling.

### Views
Five files inherit native `mrp.*` view ids directly (`mrp.mrp_production_form_view`, `mrp.mrp_production_tree_view`, `mrp.mrp_bom_form_view` ×3, `mrp.mrp_bom_tree_view` ×2, `mrp.view_mrp_bom_filter`). `omni_budget`'s own production view inherits `omni_ops.omni_mrp_production_form` (an omni_ops-derived id, transitively anchored on the mrp form, not on mrp's id directly).

### `omni_budget`
Only one native-field coupling: `production_id.sale_line_id` (read in `_compute_sale_order_id`/`action_create_budget`). Everything else it reads off `production_id` (`has_fob_service`, `has_freight_service`, `has_lod_service`) is itself an **omni_ops custom field**, not a native mrp one — so omni_budget's real exposure to an mrp replacement is small and one level removed. No `mrp.workorder` coupling at all.

### `quotation`
- `_get_bom_for_service_scope` queries `mrp.bom` directly using omni_ops-added fields (`service_scope`, `type='service'`).
- `order.bridge.mixin`'s freight implementation: `_bridge_record_model()` → `'mrp.production'`; `_bridge_vals()` writes native fields (`product_id`, `product_qty`, `bom_id`, `sale_line_id`, `company_id`); **`_bridge_create()` calls `mo.action_confirm()` directly** — the single most consequential call site in this whole inventory, since it's what triggers `_compute_workorder_ids` and everything downstream.
- `quotation/views/rename_views.xml` references `sale_mrp` but its entire body is commented out — a dead file, not a live dependency. Worth deleting as an unrelated freebie, not counted below.

### Manifests
`omni_ops` and `quotation` both declare `mrp` **directly**. `omni_budget` only depends on it **transitively** through `omni_ops`. No module declares `sale_mrp` as live.

---

## 3. Decisions (resolved)

**D1 — Scope of "process engine": decided.** Of the four things `mrp` gives
freight ops today — (a) BOM/template → step generation, (b) step
sequencing/dependency, (c) work-center/resource assignment with
calendar-based duration, (d) a state machine + scheduling UI — the actual
need is narrower than mrp's own shape:
- **(a) Template → step generation: required.** This is the real,
  load-bearing piece — a product needs to resolve to "what work does this
  imply."
- **(b) Step sequencing/dependency: optional.** Useful, not core. The
  engine should support it (a step can declare what it's blocked by) but
  nothing downstream should require it to exist.
- **(c) Work-center/resource assignment, calendar-based duration: dropped
  entirely.** Confirmed not used — freight work is outsourced to third-party
  suppliers, so there is no internal resource to schedule and no reliable
  basis to estimate duration against. `omni_mrp_workcenter.py` and
  `_set_dates` have no replacement; they're just not carried forward.
- **(d) A full mrp-style state machine: not needed.** mrp's work-order state
  machine exists to support quality checks, capacity blocking, and
  multi-operator scheduling — none of which apply here. A simple status per
  step (not unlike `trading.trade`'s own `draft`/`confirmed`/`closed`) is
  sufficient; anything richer would be building capability nobody asked for.

Net effect: the engine is **templates (required) + steps with optional
sequencing (lightweight) + simple status (no formal state machine)** — a
smaller build than originally scoped, since (c) and (d) are the two most
expensive pieces of `mrp` to replace and neither is needed.

**D2 — `service.state.mixin`'s `hasattr(record, 'button_start')` branch: not
a decision, a consequence.** Once nothing is a real `mrp.workorder` record
anymore, that check is permanently `False` — there is no "keep mrp as an
option" path once the manifest dependency is dropped. This isn't something
to choose; it's something to *verify*: the `write()` fallback becomes the
**only** code path, and today it has never actually been exercised as the
real path (mrp's own methods did the work). Folded into Phase 3 below as a
required verification step, not listed as an open decision.

**D3 — `_set_dates`'s behavior: resolved by D1.** Dropped, per (c) above.

**D4 — `omni_budget`'s `production_id`: decided.** The new anchor model gets
its **own name** (not a `mrp.production`-adjacent one for continuity). This
does mean `omni_budget`'s `production_id` field's comodel, and every
`related='production_id.xxx'` field reading `has_fob_service`/
`has_freight_service`/`has_lod_service`, needs updating in Phase 6 — but
per §2, `omni_budget`'s only *native*-field coupling was `sale_line_id`, so
this is a comodel/rename change, not new logic.

---

## 4. Phased plan (scoped per the resolved decisions above)

Ordered so nothing downstream is migrated before what it depends on is
proven. Dropping (c) and (d) removes what would have been Phase 5
(work-center/resource) entirely, and shrinks Phase 3 to a status field
instead of a state machine.

### Phase 0 — Build the core engine (no omni_ops changes yet)
Build `shared/process_bridge`: `process.bridge.mixin` (anchor side —
`process_state`, optional `step_ids`) and `process.step.mixin` (step side —
`sequence`, a simple `state` — not a full state machine —
`blocked_by_step_ids` as an optional field, no required sequencing). Prove
it against `ele_trading` first (adopting `process.bridge.mixin` with zero
steps, replacing its existing `status` field) as a real, working, low-risk
second consumer — not a placeholder. Characterization tests on
`trading.trade`'s current `status`/`action_confirm` behavior before
touching it, exactly as done for `budget_bridge`.

### Phase 1 — Template/step generation (replaces `_bom_find` + `_compute_workorder_ids`)
Design a generic "service template" concept (replacing `mrp.bom` +
`omni.service.scope.mixin`'s operation rewriting) that resolves a product to
a set of step definitions, and generates `process.step.mixin`-based records
from it on order confirmation — replacing `_create_service_workorders()`'s
job, but as the *only* path (not a branch alongside mrp's own routing
logic, since there is no mrp underneath anymore). No work-center/resource
field on the generated steps — dropped per D1.

### Phase 2 — Redirect `quotation`'s bridge
Change `_bridge_record_model()` and `_bridge_vals()` to target the new
anchor model instead of `'mrp.production'`, and replace the direct
`mo.action_confirm()` call with the new engine's own confirm/step-generation
entry point. This is the cutover moment — `omni_ops` stops receiving new
work orders via `mrp`'s pipeline from this point on.

### Phase 3 — Migrate to a simple step status
Move `omni_mrp_workorder.py`'s state logic (`action_start`/`action_finish`)
onto `process.step.mixin`'s own simple status field/transitions — no
quality checks, no `qty_produced`, no cascading production-state side
effects, since none of that applied to outsourced work in the first place.
**Required verification per D2:** confirm `service.state.mixin`'s `write()`
fallback path — now the only path, permanently — actually produces correct
behavior on its own, since it was previously untested as the real path.

### Phase 4 — Sequencing (optional, lightweight)
Replace `blocked_by_workorder_ids` writes in `_add_sequential_dependencies`
with `process.step.mixin`'s own `blocked_by_step_ids` where it's actually
used — this is closer to a rename than new logic. Since sequencing is
optional per D1, nothing else in the engine should assume every step
declares a dependency.

### Phase 5 — Views and cleanup
Rebuild the five views currently inheriting native `mrp.*` ids against the
new engine's own models. Retarget `omni_budget`'s `production_id` to the new
model's own name per D4, updating its `related=` fields accordingly. Drop
`mrp` from `omni_ops`'s and `quotation`'s manifest `depends`. Delete
`quotation/views/rename_views.xml` (confirmed dead — commented out in full)
as an unrelated freebie.

---

## 5. What this plan deliberately does not do

- **Replicate mrp's scheduling UI, work-center capacity planning, or
  calendar-based duration estimation.** Confirmed not needed — freight work
  is outsourced, so there's no internal resource to schedule and no
  reliable basis to estimate duration. This is not deferred, it's dropped.
- **Build a formal state machine for steps.** A simple status field covers
  the actual need; mrp's richer state machine exists for quality checks and
  multi-operator scheduling that don't apply here.
- **Touch `ele_trading_budget`/`omni_budget`'s already-shared
  `budget_bridge`/`order_bridge` mixins.** Those are unrelated,
  already-verified pieces; this plan only adds a third mixin pair alongside
  them, not a rework.
- **Start Phase 1+ before Phase 0 is proven against a real second
  consumer.** `ele_trading` adopting the anchor mixin with zero steps is the
  cheapest possible validation that the shape isn't freight-specific, and
  it's free to do before any omni_ops risk is taken on.
