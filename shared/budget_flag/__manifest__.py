# budget_flag/__manifest__.py
{
    'name': 'Budget Flag',
    'summary': 'Shared has_budget flag for any anchor model that tracks budgets via a budget_ids One2many.',
    'description': """
    Provides `budget.flag.mixin`, an AbstractModel supplying `has_budget`
    (computed from a `budget_ids` One2many the including model defines).
    Extracted after trading.trade's and mrp.production's budget bridges
    (trading_budget, omni_budget) were found to duplicate this exact field
    pair, including the field name, independently. Include it via
    `_inherit` alongside whatever the anchor model already inherits -- it
    adds nothing else, so it never displaces existing behavior.
    """,
    'author': "Elewa Company Limited",
    'website': "https://www.elewa.ke",
    'category': 'Sales',
    'version': '19.0.1.0.0',
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
    ],
    'installable': True,
    # Shared model library consumed by bridge modules -- not a user-facing app,
    # so it must not appear as an installable App card.
    'application': False,
    'license': 'LGPL-3'
}
