# -*- coding: utf-8 -*-
{
    'name': "Freight Operations Budgets",

    'summary': "Optional planned-vs-actual budgeting for freight manufacturing orders.",

    'description': """
    Adds a budget to each freight file: planned and actual cost per service
    type (FOB / Freight / Destination), charges copied from the originating
    quotation, margin tracking, and cost lines that can be actualised
    through expenses.

    Extracted from omni_ops as an optional add-on, mirroring how trading_budget
    layers onto trading. Uninstalling it removes the budgeting feature only,
    leaving freight operations intact. Anchored on omni.ops.file since
    docs/PROCESS_ENGINE_MIGRATION_PLAN.md Phase 5 retired the legacy
    mrp.production-based Operation Orders path entirely.
    """,

    'author': "Elewa Company Limited",
    'website': "https://www.elewa.ke",

    'category': 'Logistics',
    # 1.0.1 renames the budget_id anchor to mrp_budget_id; see
    # migrations/19.0.1.0.1/pre-migrate.py
    'version': '19.0.1.0.1',

    'depends': ['omni_ops', 'budgets', 'budgets_hr_expense', 'budget_bridge'],

    'data': [
        'security/ir.model.access.csv',
        'data/omni_mrp_budget_sequence.xml',
        'views/omni_mrp_budget_views.xml',
        'views/omni_ops_file_views.xml',
        'views/hr_expense_views.xml',
    ],

    'assets': {
        # Styles the "Expense Submitted" decoration on the budget line list
        # (decoration-expense-submitted -> .text-expense-submitted). Used only
        # here; this used to be a dependency on `operations` for one CSS file.
        'web.assets_backend': [
            'omni_budget/static/src/css/budget_decoration.css',
        ],
    },

    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
