# -*- coding: utf-8 -*-
{
    'name': "Vendor Bill Validation Workflow",

    'summary': "Approval workflow for vendor bills, with management or operations routing.",

    'description': """
    Adds an approval status to vendor bills, separate from the accounting state:
    draft -> awaiting validation -> validated. A bill can be routed to management
    (which schedules an activity for the approver) or to operations (which raises
    an hr.expense from the bill and validates the bill once that expense is
    approved). Rejection captures a reason on the chatter.
    """,

    'author': "Elewa Company Limited",
    'website': "https://www.elewa.ke",

    'category': 'Accounting',
    'version': '19.0.1.0.0',

    'depends': ['account', 'hr_expense'],

    'data': [
        'security/ir.model.access.csv',
        'wizard/account_move_wizards_views.xml',
        'views/res_config_settings_views.xml',
        'views/account_move_views.xml',
        'views/hr_expense_views.xml',
    ],

    'demo': [
        'demo/demo.xml',
    ],

    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
