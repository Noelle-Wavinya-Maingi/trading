# Process Bridge Mixin

Generic operational steps, sequencing, and template generation for any
anchor model, without depending on Odoo's `mrp` app.

## Depends on
`base`

## What it provides

- **`process.bridge.mixin`** — include on an anchor model (`trading.trade`,
  a freight file) that may or may not have steps. Supplies `has_steps`,
  computed from a `step_ids` One2many the including model must define
  itself under that exact name (`@api.depends('step_ids')` is hardcoded in
  the mixin, the same way Odoo's own conventional field names are
  load-bearing — do not rename `step_ids` on an including model). Zero
  steps is a fully supported case, not a placeholder.
- **`process.step.mixin`** — include on a vertical's own concrete step
  model. Supplies `sequence`, a plain `state` (draft/in_progress/done —
  deliberately not a full scheduling engine, since outsourced operational
  work has no internal resource to schedule against), and
  `action_start()`/`action_done()` transitions. Step-to-step dependency
  (`blocked_by_step_ids`) is left to the including model, since its comodel
  is that same concrete step model.
- **`process.template.mixin`** / **`process.template.step.mixin`** — a
  reusable blueprint (header + lines) that generates `process.step.mixin`
  records for an anchor via `generate_steps(anchor)`. Replaces what
  `mrp.bom` did for freight, without `mrp` underneath. "Which template
  applies" is left to each vertical's own `search()`; only the generation
  shape (resolve template lines → create step records) is shared.

**Current consumers:** `ele_trading` (`trading.trade`, no concrete step
model registered yet) and `omnifreight`'s `omni_ops` (its own step/template
models).

## Automated tests

`tests/test_process_bridge_mixin.py` exercises `has_steps`, the step state
transitions, and `generate_steps()` against a test-only
host/step/template/template-step model set in `models/` (not `tests/`, for
the same registry-timing reason as `order_bridge`'s test host).

See [docs/PROCESS_ENGINE_MIGRATION_PLAN.md](../../docs/PROCESS_ENGINE_MIGRATION_PLAN.md)
for the phased plan this module implements the early phases of.
