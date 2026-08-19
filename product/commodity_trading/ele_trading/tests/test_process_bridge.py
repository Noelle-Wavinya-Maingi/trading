# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestProcessBridge(TransactionCase):
    """Proves shared/process_bridge's anchor mixin (process.bridge.mixin)
    works for a genuine zero-step consumer -- trading.trade adopts it with
    no step-generation logic at all, to validate the shape isn't
    freight-specific before any real omni_ops migration is attempted. See
    docs/PROCESS_ENGINE_MIGRATION_PLAN.md Phase 0."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product = cls.env['product.product'].create({
            'name': 'Test Commodity',
            'type': 'consu',
        })

    def _create_trade(self, **vals):
        base_vals = {'trade_type': 'long', 'product_id': self.product.id}
        base_vals.update(vals)
        return self.env['trading.trade'].create(base_vals)

    def test_has_steps_is_false_by_default(self):
        trade = self._create_trade()
        self.assertFalse(trade.step_ids)
        self.assertFalse(trade.has_steps)

    def test_has_steps_becomes_true_once_a_step_is_linked(self):
        trade = self._create_trade()
        self.env['trading.trade.step'].create({
            'name': 'Test Step',
            'ele_trade_id': trade.id,
        })

        self.assertTrue(trade.has_steps)

    def test_has_steps_reverts_to_false_once_the_step_is_removed(self):
        trade = self._create_trade()
        step = self.env['trading.trade.step'].create({
            'name': 'Test Step',
            'ele_trade_id': trade.id,
        })
        self.assertTrue(trade.has_steps)

        step.unlink()

        self.assertFalse(trade.has_steps)

    def test_step_defaults_to_draft_and_transitions_via_actions(self):
        trade = self._create_trade()
        step = self.env['trading.trade.step'].create({
            'name': 'Test Step',
            'ele_trade_id': trade.id,
        })
        self.assertEqual(step.state, 'draft')

        step.action_start()
        self.assertEqual(step.state, 'in_progress')

        step.action_done()
        self.assertEqual(step.state, 'done')

    def test_step_blocked_by_another_step(self):
        trade = self._create_trade()
        first = self.env['trading.trade.step'].create({
            'name': 'First Step',
            'ele_trade_id': trade.id,
        })
        second = self.env['trading.trade.step'].create({
            'name': 'Second Step',
            'ele_trade_id': trade.id,
            'blocked_by_step_ids': [(4, first.id)],
        })

        self.assertIn(first, second.blocked_by_step_ids)
