# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.tests import tagged
from odoo.exceptions import ValidationError


@tagged('post_install', '-at_install')
class TestBudgetBridgeActions(TransactionCase):
    """Characterizes trading_trade_budget_bridge.py's action_create_budget/
    action_view_budget and budget_state as they exist today, before
    shared/budget_bridge absorbs their duplicated action-dict shape and
    related field (also duplicated, field-for-field, in omni_budget's
    mrp_production.py). Pins down current behavior so the extraction can be
    verified as a pure relocation, not a behavior change."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product = cls.env['product.product'].create({
            'name': 'Test Commodity',
            'type': 'consu',
        })
        cls.trade = cls.env['trading.trade'].create({
            'ele_trade_type': 'long',
            'product_id': cls.product.id,
        })

    def test_action_create_budget_creates_a_budget_and_returns_a_form_action(self):
        action = self.trade.action_create_budget()

        self.assertEqual(len(self.trade.budget_ids), 1)
        self.assertEqual(action['res_model'], 'trading.trade.budget')
        self.assertEqual(action['res_id'], self.trade.budget_ids.id)
        self.assertEqual(action['view_mode'], 'form')
        self.assertEqual(action['target'], 'current')

    def test_action_create_budget_raises_if_one_already_exists(self):
        self.trade.action_create_budget()

        with self.assertRaises(ValidationError):
            self.trade.action_create_budget()

    def test_action_view_budget_returns_a_form_action_for_the_budget(self):
        self.trade.action_create_budget()

        action = self.trade.action_view_budget()

        self.assertEqual(action['res_model'], 'trading.trade.budget')
        self.assertEqual(action['res_id'], self.trade.budget_id.id)
        self.assertEqual(action['view_mode'], 'form')
        self.assertEqual(action['target'], 'current')

    def test_action_view_budget_raises_if_none_exists(self):
        with self.assertRaises(ValidationError):
            self.trade.action_view_budget()

    def test_budget_state_follows_the_budgets_state(self):
        self.trade.action_create_budget()
        self.assertEqual(self.trade.budget_state, 'draft')

        self.trade.budget_id.action_confirm()
        self.assertEqual(self.trade.budget_state, 'confirmed')
