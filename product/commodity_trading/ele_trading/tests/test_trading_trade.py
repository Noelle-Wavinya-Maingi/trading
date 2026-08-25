# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestTradingTrade(TransactionCase):
    """Exercises trading_trade.py's own CRUD/workflow: sequence assignment on
    create(), the draft->confirmed transition, and write()'s auto-recompute
    of the trade's derived fields."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product = cls.env['product.product'].create({
            'name': 'Test Commodity',
            'type': 'consu',
        })

    def _create_trade(self, ele_trade_type='long', **vals):
        base_vals = {
            'ele_trade_type': ele_trade_type,
            'product_id': self.product.id,
        }
        base_vals.update(vals)
        return self.env['trading.trade'].create(base_vals)

    # ------------------------------------------------------------------
    # Sequence assignment on create().
    # ------------------------------------------------------------------
    def test_create_assigns_long_sequence_name(self):
        trade = self._create_trade('long')
        self.assertTrue(trade.name.startswith('TRD/LONG/'))

    def test_create_assigns_short_sequence_name(self):
        trade = self._create_trade('short')
        self.assertTrue(trade.name.startswith('TRD/SHORT/'))

    def test_create_respects_an_explicit_name(self):
        """If the caller passes a real name, create() must not overwrite it
        with a sequence -- the 'New' check is what gates sequence assignment."""
        trade = self._create_trade('long', name='Custom Name')
        self.assertEqual(trade.name, 'Custom Name')

    # ------------------------------------------------------------------
    # action_confirm().
    # ------------------------------------------------------------------
    def test_action_confirm_moves_draft_to_confirmed(self):
        trade = self._create_trade()
        self.assertEqual(trade.ele_status, 'draft')

        trade.action_confirm()

        self.assertEqual(trade.ele_status, 'confirmed')

    def test_action_confirm_is_a_noop_once_already_confirmed(self):
        """Calling action_confirm() again on an already-confirmed trade must
        not raise or otherwise misbehave -- the method only acts on 'draft'."""
        trade = self._create_trade()
        trade.action_confirm()
        self.assertEqual(trade.ele_status, 'confirmed')

        trade.action_confirm()

        self.assertEqual(trade.ele_status, 'confirmed')

    # ------------------------------------------------------------------
    # action_close_trade() / _auto_close_if_fully_matched().
    # ------------------------------------------------------------------
    def test_action_close_trade_closes_a_confirmed_trade(self):
        trade = self._create_trade()
        trade.action_confirm()

        trade.action_close_trade()

        self.assertEqual(trade.ele_status, 'closed')

    def test_action_close_trade_is_a_noop_on_a_draft_trade(self):
        trade = self._create_trade()
        self.assertEqual(trade.ele_status, 'draft')

        trade.action_close_trade()

        self.assertEqual(trade.ele_status, 'draft')

    def test_auto_close_ignores_a_draft_trade_even_if_fully_matched(self):
        """_auto_close_if_fully_matched() only acts on 'confirmed' trades --
        matching the spec on trading_trade.py."""
        trade = self._create_trade()
        self.assertEqual(trade.ele_status, 'draft')

        trade._auto_close_if_fully_matched()

        self.assertEqual(trade.ele_status, 'draft')

    # ------------------------------------------------------------------
    # write() auto-recompute.
    # ------------------------------------------------------------------
    def test_write_price_triggers_recompute_without_manual_call(self):
        """write() must recompute derived fields itself -- callers shouldn't
        need to call _compute_all_trade_fields() after a plain price write."""
        trade = self._create_trade(quantity=10.0, price=0.0)
        self.assertAlmostEqual(trade.ele_price_in_base_currency, 0.0, places=2)

        trade.write({'price': 50.0})

        # Same currency as reporting currency by default, so the converted
        # value should track the raw price directly and immediately.
        self.assertAlmostEqual(trade.ele_price_in_base_currency, 50.0, places=2)

    def test_write_to_the_same_value_is_a_safe_noop(self):
        """Writing a field back to its current value must not error or
        disturb already-computed values, whether or not that field is in
        write()'s manual recompute trigger list."""
        trade = self._create_trade(quantity=10.0, price=50.0)
        before = trade.ele_price_in_base_currency

        trade.write({'ele_trade_type': trade.ele_trade_type})

        self.assertAlmostEqual(trade.ele_price_in_base_currency, before, places=2)
