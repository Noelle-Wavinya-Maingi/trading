# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestManufacturingOrderCreation(TransactionCase):
    """Exercises omnifreight_quotation.py's manufacturing-order creation,
    now migrated onto shared/order_bridge's mixin. Originally written to
    characterize the pre-migration code (including its missing dedup
    guard); the one deliberate change that migration made -- fixing that
    gap -- is reflected below as the new expected behavior."""

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

        # 'code' is passed explicitly to avoid omni_bom.py's _generate_code(),
        # which currently crashes on any service BOM created via a plain
        # create() call (self.id has no .origin once it's a real database
        # id, not a NewId) -- a pre-existing bug, unrelated to this test,
        # flagged separately.
        cls.bom = cls.env['mrp.bom'].create({
            'product_tmpl_id': cls.freight_product.product_tmpl_id.id,
            'product_qty': 1.0,
            'type': 'service',
            'service_scope': 'fob',
            'code': 'TEST-FOB-BOM',
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

    def test_confirming_a_freight_line_creates_one_manufacturing_order(self):
        order = self._create_quotation(self.freight_product)
        order.action_confirm()

        line = order.order_line.filtered(lambda l: l.product_id == self.freight_product)
        mos = self.env['mrp.production'].search([('sale_line_id', '=', line.id)])

        self.assertEqual(len(mos), 1)
        self.assertEqual(mos.bom_id, self.bom)

    def test_confirming_a_non_freight_line_creates_no_manufacturing_order(self):
        order = self._create_quotation(self.other_product)
        order.action_confirm()

        mos = self.env['mrp.production'].search([('origin', '=', order.name)])
        self.assertFalse(mos)

    def test_reconfirming_does_not_create_a_duplicate_manufacturing_order(self):
        """Was a known gap (see git history for this test): every confirm
        used to create a fresh MO with no check. order.bridge.mixin's
        _bridge_find_existing now looks one up by sale_line_id first, so a
        second confirm updates in place instead of duplicating."""
        order = self._create_quotation(self.freight_product)
        order.action_confirm()

        line = order.order_line.filtered(lambda l: l.product_id == self.freight_product)
        order._bridge_sync()

        mos = self.env['mrp.production'].search([('sale_line_id', '=', line.id)])
        self.assertEqual(len(mos), 1)
