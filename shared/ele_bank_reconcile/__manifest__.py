# -*- coding: utf-8 -*-
{
    'name': "Bank Reconciliation Match Quality",

    'summary': "Flags bank statement lines as perfect/partial matches during reconciliation.",

    'description': """
    Classifies each bank statement line by how confidently it reconciles:
    a line already backed by an invoice/bill, or recognisable as a bank fee,
    internal transfer or forex movement, is a perfect match; anything else is
    partial and needs review.

    Extracted from omni_ops. This module has no freight, manufacturing or
    budgeting dependency -- it only extends account.bank.statement.line and is
    usable by any client on any chart of accounts. The account codes, fee
    patterns and transfer keywords it matches on are per-company settings
    rather than hardcoded values.
    """,

    'author': "Elewa Company Limited",
    'website': "https://www.elewa.ke",

    'category': 'Accounting',
    'version': '19.0.1.0.0',

    'depends': ['account'],

    'data': [
        'views/res_config_settings_views.xml',
        'views/account_bank_statement_line_views.xml',
    ],

    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
