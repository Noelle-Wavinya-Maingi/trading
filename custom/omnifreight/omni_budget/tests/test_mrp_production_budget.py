# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestMrpProductionBudget(TransactionCase):
    """Characterizes mrp_production.py's has_budget/budget_ids as they exist
    today, before shared/budget_bridge extracts them into a mixin shared
    with trading.trade's identical field pair. Pins down current behavior so
    the extraction can be verified as a pure relocation, not a behavior
    change."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product = cls.env['product.product'].create({
            'name': 'Test Freight Forwarding Service',
            'type': 'consu',
        })
        cls.production = cls.env['mrp.production'].create({
            'product_id': cls.product.id,
            'product_qty': 1.0,
            'product_uom_id': cls.product.uom_id.id,
        })

    def test_has_budget_is_false_with_no_linked_budget(self):
        self.assertFalse(self.production.budget_ids)
        self.assertFalse(self.production.has_budget)

    def test_has_budget_becomes_true_once_a_budget_is_linked(self):
        self.env['omni.mrp.budget'].create({
            'production_id': self.production.id,
        })

        self.assertTrue(self.production.has_budget)

    def test_has_budget_reverts_to_false_once_the_budget_is_removed(self):
        budget = self.env['omni.mrp.budget'].create({
            'production_id': self.production.id,
        })
        self.assertTrue(self.production.has_budget)

        budget.unlink()

        self.assertFalse(self.production.has_budget)
