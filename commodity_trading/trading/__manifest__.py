# -*- coding: utf-8 -*-
{
    'name': "Trading",
    'summary': "Manage trading operations and related processes",
    'description': """
    Trading Module
    This module provides comprehensive features for managing trading operations, including:
    - Trade management: Create and manage trade records, including details such as trade type, products involved, quantities, and values.
    - Partner management: Manage trading partners, including suppliers and customers, with detailed contact information and trade history.
    - Trade documentation: Generate and manage trade-related documents such as invoices, delivery notes, and contracts.
    - Reporting and analytics: Access detailed reports and analytics on trading activities, including trade performance, partner analysis, and financial insights.
    """,
    'author': "Elewa Company Limited",
    'website': "https://www.elewa.ke",
    'category': 'Sales',
    'version': '19.0.1.0.0',

    # Dependencies
    # 'operations' was declared here but nothing in this module references
    # any of its models or config fields -- a phantom dependency.
    'depends': [
        'base', 'stock', 'sale', 'purchase', 'hr_expense'
    ],

    # Data files loaded at installation
    'data': [
        'security/ir.model.access.csv',

        'data/sequence.xml',

        'views/trading_trade_views.xml',
        # 'views/trading_trade_budget_views.xml',
        'views/menu.xml',
        'views/trading_futures_views.xml',
        'views/purchase_order.xml',
        'views/stock_views.xml',
        'views/sale_view.xml',
        'views/account_move_line_view.xml',
        'views/product_template.xml',
        # 'views/hr_expense_views.xml',
        'views/res_config_settings_view.xml',
    ],

    'assets': {
        'web.assets_backend': [
            'trading/static/src/scss/trading_kpi_cards.scss',
        ],
    },

    # Installation settings
    'installable': True,
    'application': True,
    'license': 'LGPL-3'
}