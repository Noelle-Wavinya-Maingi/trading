# -*- coding: utf-8 -*-
from odoo import fields, models


class OrderBridgeTestHost(models.Model):
    """Test-only stand-in for a real order model (sale.order, purchase.order).

    order.bridge.mixin only ever actually merges into sale.order when some
    real vertical module declares `_inherit = ['sale.order',
    'order.bridge.mixin']` -- testing the registry mechanism against
    sale.order directly would only work by coincidence of whatever vertical
    modules happen to be installed alongside order_bridge in a given test
    run, which is exactly the kind of untested assumption that let two
    verticals' hooks silently collide on sale.order for as long as they
    did. This model lets shared/order_bridge/tests/test_order_bridge_mixin.py
    prove the mechanism correct on its own, with order_bridge installed
    alone.

    Deliberately lives in models/, not tests/: a model defined only inside a
    tests/ file is never added to the registry (Odoo builds the registry
    before importing test modules, only importing them afterwards to run
    the tests they contain, not to contribute schema). No view, no menu, no
    security beyond the default -- nothing here is ever exposed to a real
    user, it exists purely so a TransactionCase can create records of it."""
    _name = 'order.bridge.test.host'
    _description = 'Order Bridge Test Host'
    _inherit = ['order.bridge.mixin']

    name = fields.Char(default='Test Host')
