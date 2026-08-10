# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestFreightFileCreation(TransactionCase):
    """Exercises omnifreight_quotation.py's freight-file creation, now on
    omni.ops.file via shared/process_bridge instead of mrp.production via
    mrp.bom -- see docs/PROCESS_ENGINE_MIGRATION_PLAN.md Phase 2. Originally
    written (as test_manufacturing_order_creation.py) to characterize the
    order_bridge migration's dedup fix; that behavior carries over unchanged
    here, just against the new anchor model."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env['res.partner'].create({'name': 'Test Freight Customer'})
        cls.cargo_type = cls.env['omnifreight.cargo.type'].create({'name': 'General Cargo'})

        cls.freight_product = cls.env['product.product'].create({
            'name': 'Freight Forwarding Service',
            'type': 'omni_service',
        })
        cls.other_product = cls.env['product.product'].create({
            'name': 'Office Supplies',
            'type': 'consu',
        })

        cls.template = cls.env['omni.service.step.template'].create({
            'name': 'FOB Only',
            'service_scope': 'fob',
            'template_step_ids': [
                (0, 0, {'name': 'Customs Clearance', 'sequence': 10, 'service_type': 'fob'}),
            ],
        })

    def _create_quotation(self, product, qty=1.0):
        return self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'quote_type': 'fob_only',
            'container_type': '20dv',
            'contents': [(4, self.cargo_type.id)],
            'order_line': [(0, 0, {
                'product_id': product.id,
                'product_uom_qty': qty,
            })],
        })

    def test_confirming_a_freight_line_creates_one_freight_file(self):
        order = self._create_quotation(self.freight_product)
        order.action_confirm()

        line = order.order_line.filtered(lambda l: l.product_id == self.freight_product)
        files = self.env['omni.ops.file'].search([('sale_line_id', '=', line.id)])

        self.assertEqual(len(files), 1)
        self.assertEqual(files.step_ids.mapped('name'), ['Customs Clearance'])

    def test_confirming_a_non_freight_line_creates_no_freight_file(self):
        order = self._create_quotation(self.other_product)
        order.action_confirm()

        files = self.env['omni.ops.file'].search([('origin', '=', order.name)])
        self.assertFalse(files)

    def test_reconfirming_does_not_create_a_duplicate_freight_file(self):
        """order.bridge.mixin's _bridge_find_existing looks one up by
        sale_line_id first, so a second confirm updates in place instead of
        duplicating -- unchanged by the mrp.production -> omni.ops.file
        cutover."""
        order = self._create_quotation(self.freight_product)
        order.action_confirm()

        line = order.order_line.filtered(lambda l: l.product_id == self.freight_product)
        order._bridge_sync()

        files = self.env['omni.ops.file'].search([('sale_line_id', '=', line.id)])
        self.assertEqual(len(files), 1)

    def test_confirming_with_no_matching_template_warns_instead_of_failing_silently(self):
        """A missing step template used to fail with zero feedback: the
        order confirmed fine and nothing told anyone why no file appeared.
        Confirming still succeeds (a missing template must not block the
        sale), but now posts a chatter message so it's visible on the order
        itself, not just a UserError caught and discarded."""
        order = self._create_quotation(self.freight_product)
        order.quote_type = 'freight_only'  # no template exists for this scope

        order.action_confirm()

        self.assertEqual(order.state, 'sale')
        files = self.env['omni.ops.file'].search([
            ('sale_line_id.order_id', '=', order.id),
        ])
        self.assertFalse(files)
        self.assertTrue(any(
            'No freight step template found' in (m.body or '')
            for m in order.message_ids
        ))
