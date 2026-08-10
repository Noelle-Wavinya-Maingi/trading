# process_bridge/__manifest__.py
{
    'name': 'Process Bridge Mixin',
    'summary': 'Generic operational steps/sequencing for any anchor model, independent of mrp.',
    'description': """
    Provides two AbstractModels for tracking optional, lightweight
    operational steps on any anchor record, without depending on Odoo's
    `mrp` app:

    - `process.bridge.mixin`: include on an anchor model (e.g. trading.trade,
      a freight file) that may or may not have steps. Supplies `has_steps`,
      computed from a `step_ids` One2many the including model defines --
      same pattern as budget_bridge's `has_budget`/`budget_ids`. An anchor
      with zero steps is a fully supported, first-class case, not a
      placeholder for a future feature.
    - `process.step.mixin`: include on a vertical's own concrete step model.
      Supplies `sequence`, a simple `state` (draft/in_progress/done --
      deliberately not a full state machine: no quality checks, no
      capacity/resource assignment, no calendar-based duration, since none
      of that reflects how outsourced operational work is actually
      tracked), and `action_start`/`action_done` transitions. Dependency
      between steps
      (`blocked_by_step_ids`) is left to the including model to define, since
      its comodel is that same concrete step model -- exactly why
      `budget_ids`/`step_ids` themselves live on the including model, not
      the mixin.

    See docs/PROCESS_ENGINE_MIGRATION_PLAN.md for the plan this implements
    Phase 0 of.
    """,
    'author': "Elewa Company Limited",
    'website': "https://www.elewa.ke",
    'category': 'Sales',
    'version': '19.0.1.0.0',
    'depends': ['base'],
    'data': [],
    'installable': True,
    # Shared model library consumed by bridge modules -- not a user-facing app,
    # so it must not appear as an installable App card.
    'application': False,
    'license': 'LGPL-3'
}
