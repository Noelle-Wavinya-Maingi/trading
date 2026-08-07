# order_bridge/__manifest__.py
{
    'name': 'Order Bridge Mixin',
    'summary': 'Shared confirm-hook skeleton for deriving an industry operational record from a confirmed order.',
    'description': """
    Provides `order.bridge.mixin`, a template-method AbstractModel for the
    "confirm an order -> derive an industry operational record" flow
    already implemented three times independently (trading.trade from both
    sale and purchase orders, mrp.production from freight quotations). The
    four-step skeleton -- filter qualifying lines, group them, create-or-
    update the target record per group, link back -- is identical across all
    three; the concrete grouping, field mapping, and update-vs-create
    strategy genuinely differ per vertical and stay as required overrides.

    Include via `_inherit` alongside whatever the source model (sale.order,
    purchase.order) already inherits -- it adds nothing else, so it never
    displaces existing behavior.
    """,
    'author': "Elewa Company Limited",
    'website': "https://www.elewa.ke",
    'category': 'Sales',
    'version': '19.0.1.0.0',
    'depends': ['sale', 'purchase'],
    'data': [],
    'installable': True,
    # Shared model library consumed by bridge modules -- not a user-facing app,
    # so it must not appear as an installable App card.
    'application': False,
    'license': 'LGPL-3'
}
