# -*- coding: utf-8 -*-
{
    'name': 'Budget Management - Expense Actualization',
    'summary': 'Auto-creates/syncs an hr.expense to back a budget line\'s actual amount.',
    'description': """
    Optional actualization backend for the `budgets` module: plugs into
    `operations.budget.line` via its `_sync_actual_source()` hook to
    auto-create, update, and remove a linked `hr.expense` as a line's
    actual amount changes. Uninstalling this module leaves `budgets` fully
    intact -- lines simply go back to trusting `actual_amount` /
    `account_move_id` as entered, with no backing document of their own.
    """,
    'author': "Your Company",
    'website': "https://www.yourcompany.com",
    'category': 'Sales',
    'version': '1.0.0',
    'depends': ['budgets', 'hr_expense'],
    'data': [],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
