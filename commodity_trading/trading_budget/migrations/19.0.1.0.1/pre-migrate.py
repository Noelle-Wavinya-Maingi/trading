# -*- coding: utf-8 -*-
"""Rename operations.budget.line.budget_id -> trade_budget_id.

Both this module and omni_budget used to add an anchor FK called `budget_id`
to the shared operations.budget.line, pointing at different models, so the two
could never be installed in the same database. Each bridge now namespaces its
own anchor.

Renaming the column in pre-migrate preserves existing links; without this Odoo
would add an empty trade_budget_id and leave the old column orphaned, silently
detaching every budget line from its budget.
"""


def migrate(cr, version):
    if not version:
        return

    cr.execute("""
        SELECT 1 FROM information_schema.columns
         WHERE table_name = 'operations_budget_line' AND column_name = 'budget_id'
    """)
    if not cr.fetchone():
        return

    cr.execute("""
        SELECT 1 FROM information_schema.columns
         WHERE table_name = 'operations_budget_line' AND column_name = 'trade_budget_id'
    """)
    if cr.fetchone():
        return

    cr.execute("ALTER TABLE operations_budget_line RENAME COLUMN budget_id TO trade_budget_id")
    cr.execute("""
        UPDATE ir_model_fields
           SET name = 'trade_budget_id'
         WHERE name = 'budget_id'
           AND model = 'operations.budget.line'
    """)
