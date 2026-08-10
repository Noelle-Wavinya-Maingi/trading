# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.tests import tagged
from odoo.exceptions import ValidationError


@tagged('post_install', '-at_install')
class TestBudgetBridgeActions(TransactionCase):
    """Characterizes mrp_production.py's action_create_budget/action_view_budget
    and budget_state as they exist today, before shared/budget_bridge absorbs
    their duplicated action-dict shape and related field (also duplicated,
    field-for-field, in trading_trade_budget_bridge.py). Pins down current
    behavior so the extraction can be verified as a pure relocation, not a
    behavior change."""

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

    def test_action_create_budget_creates_a_budget_and_returns_a_form_action(self):
        action = self.production.action_create_budget()

        self.assertEqual(len(self.production.budget_ids), 1)
        self.assertEqual(action['res_model'], 'omni.mrp.budget')
        self.assertEqual(action['res_id'], self.production.budget_ids.id)
        self.assertEqual(action['view_mode'], 'form')
        self.assertEqual(action['target'], 'current')

    def test_action_create_budget_raises_if_one_already_exists(self):
        self.production.action_create_budget()

        with self.assertRaises(ValidationError):
            self.production.action_create_budget()

    def test_action_view_budget_returns_a_form_action_for_the_active_budget(self):
        self.production.action_create_budget()

        action = self.production.action_view_budget()

        self.assertEqual(action['res_model'], 'omni.mrp.budget')
        self.assertEqual(action['res_id'], self.production.budget_id.id)
        self.assertEqual(action['view_mode'], 'form')
        self.assertEqual(action['target'], 'current')

    def test_action_view_budget_raises_if_none_exists(self):
        with self.assertRaises(ValidationError):
            self.production.action_view_budget()

    def test_budget_state_follows_the_active_budgets_state(self):
        self.production.action_create_budget()
        self.assertEqual(self.production.budget_state, 'draft')

        self.production.budget_id.action_confirm()
        self.assertEqual(self.production.budget_state, 'confirmed')
