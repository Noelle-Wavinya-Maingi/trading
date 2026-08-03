# -*- coding: utf-8 -*-
"""Rename operations.budget.line.budget_id -> mrp_budget_id.

Both this module and trading_budget used to add an anchor FK called `budget_id`
to the shared operations.budget.line, pointing at different models, so the two
could never be installed in the same database. Each bridge now namespaces its
own anchor.

The rename is guarded on trading_budget being absent: in any database that
predates this change only one of the two bridges can be installed, so a
`budget_id` column found here belongs to this module -- but the guard makes
that assumption explicit rather than implicit, and keeps the migration inert
if it is ever run somewhere unexpected.
"""


def migrate(cr, version):
    if not version:
        return

    cr.execute("SELECT 1 FROM ir_module_module WHERE name = 'trading_budget' AND state = 'installed'")
    if cr.fetchone():
        # Not ours to rename; trading_budget's own migration owns this column.
        return

    cr.execute("""
        SELECT 1 FROM information_schema.columns
         WHERE table_name = 'operations_budget_line' AND column_name = 'budget_id'
    """)
    if not cr.fetchone():
        return

    cr.execute("""
        SELECT 1 FROM information_schema.columns
         WHERE table_name = 'operations_budget_line' AND column_name = 'mrp_budget_id'
    """)
    if cr.fetchone():
        return

    cr.execute("ALTER TABLE operations_budget_line RENAME COLUMN budget_id TO mrp_budget_id")
    cr.execute("""
        UPDATE ir_model_fields
           SET name = 'mrp_budget_id'
         WHERE name = 'budget_id'
           AND model = 'operations.budget.line'
    """)
