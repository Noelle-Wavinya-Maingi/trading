# budgets/__manifest__.py
{
    'name': 'Budget Management',
    'summary': 'Shared, industry-agnostic budget line model for use by any business domain module.',
    'author': "Elewa Company Limited",
    'website': "https://www.elewa.ke",
    'category': 'Sales',
    'version': '19.0.1.0.0',
    'depends': ['base', 'mail', 'account'],
    'data': [
        'security/ir.model.access.csv',
    ],
    'installable': True,
    # Shared model library consumed by bridge modules -- not a user-facing app,
    # so it must not appear as an installable App card.
    'application': False,
    'license': 'LGPL-3' 
}