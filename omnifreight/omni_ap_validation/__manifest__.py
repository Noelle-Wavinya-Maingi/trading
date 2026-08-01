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

    Extracted from omni_ops. This module carries no freight, manufacturing or
    budgeting dependency -- the shipment fields that used to sit in the same file
    stayed behind in omni_ops -- so any client needing bill approval can install
    it on its own.
    """,

    'author': "Elewa Company",
    'website': "https://www.elewa.ke",

    'category': 'Accounting',
    'version': '1.0.0',

    'depends': ['account', 'hr_expense'],

    'data': [
        'security/ir.model.access.csv',
        'views/res_config_settings_views.xml',
        'views/account_move_views.xml',
        'views/hr_expense_views.xml',
    ],

    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
