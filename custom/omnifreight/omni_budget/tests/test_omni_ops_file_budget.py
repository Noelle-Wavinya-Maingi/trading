# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.tests import tagged
from odoo.exceptions import ValidationError


@tagged('post_install', '-at_install')
class TestOmniOpsFileBudget(TransactionCase):
    """Proves budgeting works against omni.ops.file, the anchor quotation
    actually creates now (docs/PROCESS_ENGINE_MIGRATION_PLAN.md Phase 2),
    not just the legacy mrp.production path test_budget_bridge_actions.py
    already covers. Mirrors that file's tests one-for-one against the new
    anchor, plus the has_fob/freight/lod_service flags and the
    exactly-one-anchor constraint that make the two anchors coexist on the
    same omni.mrp.budget model."""

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

    def test_action_create_budget_creates_a_budget_and_returns_a_form_action(self):
        action = self.file.action_create_budget()

        self.assertEqual(len(self.file.budget_ids), 1)
        self.assertEqual(action['res_model'], 'omni.mrp.budget')
        self.assertEqual(action['res_id'], self.file.budget_ids.id)
        self.assertEqual(action['view_mode'], 'form')
        self.assertEqual(action['target'], 'current')

    def test_action_create_budget_raises_if_one_already_exists(self):
        self.file.action_create_budget()

        with self.assertRaises(ValidationError):
            self.file.action_create_budget()

    def test_action_view_budget_returns_a_form_action_for_the_active_budget(self):
        self.file.action_create_budget()

        action = self.file.action_view_budget()

        self.assertEqual(action['res_model'], 'omni.mrp.budget')
        self.assertEqual(action['res_id'], self.file.budget_id.id)
        self.assertEqual(action['view_mode'], 'form')
        self.assertEqual(action['target'], 'current')

    def test_action_view_budget_raises_if_none_exists(self):
        with self.assertRaises(ValidationError):
            self.file.action_view_budget()

    def test_budget_state_follows_the_active_budgets_state(self):
        self.file.action_create_budget()
        self.assertEqual(self.file.budget_state, 'draft')

        self.file.budget_id.action_confirm()
        self.assertEqual(self.file.budget_state, 'confirmed')

    def test_budget_cannot_be_linked_to_both_anchors(self):
        production = self.env['mrp.production'].create({
            'product_id': self.product.id,
            'product_qty': 1.0,
            'product_uom_id': self.product.uom_id.id,
        })

        with self.assertRaises(Exception):
            self.env['omni.mrp.budget'].create({
                'production_id': production.id,
                'file_id': self.file.id,
                'currency_id': self.env.company.currency_id.id,
            })

    def test_budget_cannot_be_linked_to_neither_anchor(self):
        with self.assertRaises(Exception):
            self.env['omni.mrp.budget'].create({
                'currency_id': self.env.company.currency_id.id,
            })

    def test_service_flags_follow_the_files_own_generated_steps(self):
        template = self.env['omni.service.step.template'].create({
            'name': 'FOB + Freight',
            'service_scope': 'fob_freight',
            'template_step_ids': [
                (0, 0, {'name': 'Customs Clearance', 'sequence': 10, 'service_type': 'fob'}),
                (0, 0, {'name': 'Inland Transport', 'sequence': 20, 'service_type': 'freight'}),
            ],
        })
        template.generate_steps(self.file)

        self.assertTrue(self.file.has_fob_service)
        self.assertTrue(self.file.has_freight_service)
        self.assertFalse(self.file.has_lod_service)

        self.file.action_create_budget()
        budget = self.file.budget_id
        self.assertTrue(budget.has_fob_service)
        self.assertTrue(budget.has_freight_service)
        self.assertFalse(budget.has_lod_service)
