# -*- coding: utf-8 -*-
{
    'name': "Accounting & Budgetting",

    'summary': "Custom module for accounting and budgetting",

    'description': """This module delivers custom freight handling functionality for Omnifreight.

    Freight files (omni.ops.file), their operational steps (omni.ops.step),
    and the templates that generate them (omni.service.step.template) are
    a self-contained process engine (shared/workflow) -- no mrp
    dependency. The legacy mrp.production-based Operation Orders / Bills of
    Material path has been retired entirely; see
    docs/PROCESS_ENGINE_MIGRATION_PLAN.md Phase 5.
    """,

    'author': "Elewa Company Limited",
    'website': "https://www.elewa.ke",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Logistics',
    'version': '19.0.1.0.0',

    # any module necessary for this one to work correctly
    # Budgeting now lives in the optional omni_budget module, which depends on
    # budgets/budgets_hr_expense; core freight operations needs neither. Nor
    # does it need 'operations': nothing here referenced any of its models or
    # config fields, or the one CSS class it used to provide (that moved to
    # omni_budget, its actual and only consumer).
    'depends': ['base', 'sale', 'product', 'quotation', 'account', 'hr_expense', 'stock', 'workflow'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'data/omni_ops_file_sequence.xml',
        'views/omni_ops_menu.xml',
        'views/omni_ops_file_views.xml',
        'views/omni_service_step_template_views.xml',
        'views/omni_hr_expense_views.xml',
        'views/additional_file_operations_views.xml',
        'views/omnifreight-documents_view.xml',
        'views/omni_vessels_view.xml',
        'views/account_move_views.xml',
        'views/sale_order_views.xml',
    ],

    'application': True,
    'installable': True,
    'license': 'LGPL-3',

    # The expense-submitted decoration CSS is now provided generically by the
    # `operations` module (shared budget line UI), so no module-local asset is needed.
}

