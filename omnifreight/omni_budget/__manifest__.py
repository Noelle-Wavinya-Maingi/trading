# -*- coding: utf-8 -*-
{
    'name': "Freight Operations Budgets",

    'summary': "Optional planned-vs-actual budgeting for freight manufacturing orders.",

    'description': """
    Adds a budget to each freight manufacturing order: planned and actual cost
    per service type (FOB / Freight / Destination), charges copied from the
    originating quotation, margin tracking, and cost lines that can be actualised
    through expenses.

    Extracted from omni_ops as an optional add-on, mirroring how trading_budget
    layers onto trading. Uninstalling it removes the budgeting feature only,
    leaving freight operations intact -- previously the budget fields lived on
    omni_ops' own mrp.production extension, so core freight operations could not
    be installed without the whole budgeting feature.
    """,

    'author': "Elewa Company",
    'website': "https://www.elewa.ke",

    'category': 'Logistics',
    'version': '1.0.0',

    # `operations` is a direct dependency, not merely a transitive one via omni_ops:
    # the budget list view uses the .text-expense-submitted CSS class that only the
    # operations module's assets bundle provides.
    'depends': ['omni_ops', 'operations', 'budgets', 'budgets_hr_expense'],

    'data': [
        'security/ir.model.access.csv',
        'data/omni_mrp_budget_sequence.xml',
        'views/omni_mrp_budget_views.xml',
        'views/mrp_production_views.xml',
        'views/hr_expense_views.xml',
    ],

    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
