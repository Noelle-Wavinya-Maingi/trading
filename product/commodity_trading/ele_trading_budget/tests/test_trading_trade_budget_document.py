# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestTradingTradeBudgetDocument(TransactionCase):
    """Characterizes trading.trade.budget's own document-header behavior
    (explicit name passthrough, currency/company defaults, draft default)
    as it exists today, before shared/budget_bridge extracts it into a
    budget.document.mixin shared with omni.mrp.budget's identical fields
    and methods. test_trading_trade_budget.py already covers the sequence
    name assignment and confirm/close transitions; this fills the gaps so
    both sides of the extraction are pinned down equally."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product = cls.env['product.product'].create({
            'name': 'Test Commodity',
            'type': 'consu',
        })
        cls.trade = cls.env['trading.trade'].create({
            'trade_type': 'long',
            'product_id': cls.product.id,
        })

    def test_create_respects_an_explicitly_passed_name(self):
        budget = self.env['trading.trade.budget'].create({
            'ele_trade_id': self.trade.id,
            'currency_id': self.trade.currency_id.id,
            'name': 'Explicit Name',
        })
        self.assertEqual(budget.name, 'Explicit Name')

    def test_defaults_to_draft_state(self):
        budget = self.env['trading.trade.budget'].create({
            'ele_trade_id': self.trade.id,
            'currency_id': self.trade.currency_id.id,
        })
        self.assertEqual(budget.state, 'draft')

    def test_company_defaults_from_environment(self):
        budget = self.env['trading.trade.budget'].create({
            'ele_trade_id': self.trade.id,
            'currency_id': self.trade.currency_id.id,
        })
        self.assertEqual(budget.company_id, self.env.company)
