# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestOmniMrpBudgetDocument(TransactionCase):
    """Characterizes omni.mrp.budget's own document-header behavior (name
    sequence assignment, state defaults, action_confirm/action_close) --
    the budget.document.mixin behavior shared with trading.trade.budget.
    Anchored on omni.ops.file, the only anchor now that
    docs/PROCESS_ENGINE_MIGRATION_PLAN.md Phase 5 retired the legacy
    mrp.production path entirely."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product = cls.env['product.product'].create({
            'name': 'Test Freight Forwarding Service',
            'type': 'consu',
        })
        cls.file = cls.env['omni.ops.file'].create({
            'product_id': cls.product.id,
            'product_qty': 1.0,
        })

    def _create_budget(self):
        return self.env['omni.mrp.budget'].create({
            'file_id': self.file.id,
        })

    def test_create_assigns_budget_sequence_name(self):
        budget = self._create_budget()
        self.assertTrue(budget.name.startswith('FRT/BUD/'))

    def test_create_respects_an_explicitly_passed_name(self):
        budget = self.env['omni.mrp.budget'].create({
            'file_id': self.file.id,
            'name': 'Explicit Name',
        })
        self.assertEqual(budget.name, 'Explicit Name')

    def test_defaults_to_draft_state(self):
        budget = self._create_budget()
        self.assertEqual(budget.state, 'draft')

    def test_action_confirm_and_close_transitions(self):
        budget = self._create_budget()
        self.assertEqual(budget.state, 'draft')

        budget.action_confirm()
        self.assertEqual(budget.state, 'confirmed')

        budget.action_close()
        self.assertEqual(budget.state, 'closed')

    def test_currency_and_company_default_from_environment(self):
        budget = self._create_budget()
        self.assertEqual(budget.currency_id, self.env.company.currency_id)
        self.assertEqual(budget.company_id, self.env.company)

    def test_file_id_is_required(self):
        with self.assertRaises(Exception):
            self.env['omni.mrp.budget'].create({
                'currency_id': self.env.company.currency_id.id,
            })
