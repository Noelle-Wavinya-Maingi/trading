# -*- coding: utf-8 -*-
{
    'name': "Trading Budgets",
    'summary': "Optional Trade Budget feature for the Trading module — bridges trading.trade with the shared budgets line model.",
    'description': """
    Adds a Trade Budget (planned vs. actual cost/revenue, auto-synced from
    Bills, Invoices, and Expenses) to every trade. This is an optional
    add-on to Trading: uninstalling it removes the Budget feature only,
    leaving Trading and Budget Management both intact.
    """,
    'author': "Elewa Company Limited",
    'website': "https://www.elewa.ke",
    'category': 'Sales',
    # 1.0.1 renames the budget_id anchor to trade_budget_id; see
    # migrations/19.0.1.0.1/pre-migrate.py
    'version': '19.0.1.0.1',
    'depends': ['trading', 'budgets', 'budgets_hr_expense'],
   'data': [
        'security/ir.model.access.csv',
        'views/trading_trade_views.xml',
        'views/trading_trade_budget_views.xml',
        'views/hr_expense_views.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}