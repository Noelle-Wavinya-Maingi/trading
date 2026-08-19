# -*- coding: utf-8 -*-
{
    'name': "Bank Reconciliation Match Quality",

    'summary': "Flags bank statement lines as perfect/partial matches during reconciliation.",

    'description': """
    Classifies each bank statement line by how confidently it reconciles:
    a line already backed by an invoice/bill, or recognisable as a bank fee,
    internal transfer or forex movement, is a perfect match; anything else is
    partial and needs review.
""",

    'author': "Elewa Company Limited",
    'website': "https://www.elewa.ke",

    'category': 'Accounting',
    'version': '19.0.1.0.0',

    'depends': ['account', 'account_accountant'],

    'data': [
        'views/res_config_settings_views.xml',
        'views/account_bank_statement_line_views.xml',
    ],

    'demo': [
        'demo/demo.xml',
    ],

    'assets': {
        'web.assets_backend': [
            'ele_bank_reconcile/static/src/xml/statement_line.xml',
        ],
    },

    'installable': True,
    'application': True,
    'license': 'OEEL-1',
}
