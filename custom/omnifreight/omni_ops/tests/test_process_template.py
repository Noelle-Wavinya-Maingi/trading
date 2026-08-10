# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestProcessTemplate(TransactionCase):
    """Proves shared/process_bridge's template mixins (process.template.mixin,
    process.template.step.mixin) generate real, sequenced,
    independent-of-mrp steps for freight -- the actual load-bearing case the
    engine was built for. Anchored on omni.ops.file, the model
    docs/PROCESS_ENGINE_MIGRATION_PLAN.md Phase 2 introduced to replace
    mrp.production as quotation's order_bridge target. See
    product/commodity_trading/ele_trading/tests/test_process_bridge.py for
    the zero-step proof on the trading side."""

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
        cls.template = cls.env['omni.service.step.template'].create({
            'name': 'FOB + Freight + Destination',
            'service_scope': 'fob_freight_lod',
            'template_step_ids': [
                (0, 0, {'name': 'Customs Clearance', 'sequence': 10, 'service_type': 'fob'}),
                (0, 0, {'name': 'Inland Transport', 'sequence': 20, 'service_type': 'freight'}),
                (0, 0, {'name': 'Final Delivery', 'sequence': 30, 'service_type': 'lod'}),
            ],
        })

    def test_generate_steps_creates_one_step_per_template_line(self):
        steps = self.template.generate_steps(self.file)

        self.assertEqual(len(steps), 3)
        self.assertEqual(set(steps.mapped('name')), {'Customs Clearance', 'Inland Transport', 'Final Delivery'})
        self.assertTrue(all(step.file_id == self.file for step in steps))

    def test_generate_steps_preserves_sequence_order(self):
        steps = self.template.generate_steps(self.file)

        self.assertEqual(steps.mapped('sequence'), [10, 20, 30])
        self.assertEqual(steps.mapped('service_type'), ['fob', 'freight', 'lod'])

    def test_generate_steps_with_no_lines_returns_empty_recordset(self):
        empty_template = self.env['omni.service.step.template'].create({
            'name': 'Empty Template',
            'service_scope': 'fob',
        })

        steps = empty_template.generate_steps(self.file)

        self.assertFalse(steps)

    def test_generated_steps_default_to_draft_and_transition(self):
        steps = self.template.generate_steps(self.file)
        first_step = steps.filtered(lambda s: s.sequence == 10)
        self.assertEqual(first_step.state, 'draft')

        first_step.action_start()
        self.assertEqual(first_step.state, 'in_progress')

        first_step.action_done()
        self.assertEqual(first_step.state, 'done')

    def test_generated_steps_support_sequencing_dependency(self):
        steps = self.template.generate_steps(self.file)
        first_step = steps.filtered(lambda s: s.sequence == 10)
        second_step = steps.filtered(lambda s: s.sequence == 20)
        second_step.blocked_by_step_ids = [(4, first_step.id)]

        self.assertIn(first_step, second_step.blocked_by_step_ids)

    def test_file_has_steps_via_the_anchor_mixin(self):
        self.assertFalse(self.file.has_steps)

        self.template.generate_steps(self.file)

        self.assertTrue(self.file.has_steps)
        self.assertEqual(len(self.file.step_ids), 3)
