# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestSaleOrderTradeSync(TransactionCase):
    """Exercises sale_order.py: confirming a sale order auto-creates or
    updates a trade for tradeable lines, and closes the trade once fully
    sold."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env['res.partner'].create({'name': 'Test Customer'})
        cls.trade_product = cls.env['product.product'].create({
            'name': 'Test Cocoa',
            'type': 'consu',
        })
        cls.non_trade_product = cls.env['product.product'].create({
            'name': 'Office Supplies',
            'type': 'consu',
            'is_tradeable': False,
        })

    def _create_order(self, product, qty=10.0, price_unit=100.0):
        return self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'order_line': [(0, 0, {
                'product_id': product.id,
                'product_uom_qty': qty,
                'price_unit': price_unit,
            })],
        })

    def test_confirming_order_with_tradeable_line_creates_a_short_trade(self):
        order = self._create_order(self.trade_product, qty=10.0, price_unit=100.0)
        order.action_confirm()

        self.assertTrue(order.trade_id)
        trade = order.trade_id
        self.assertEqual(trade.trade_type, 'short')
        self.assertEqual(trade.status, 'confirmed')
        self.assertEqual(trade.product_id, self.trade_product)
        self.assertAlmostEqual(trade.quantity, 10.0, places=2)
        self.assertAlmostEqual(trade.sales_price, 100.0, places=2)
        self.assertIn(order, trade.sale_order_ids)

    def test_confirming_order_with_only_non_tradeable_lines_creates_no_trade(self):
        order = self._create_order(self.non_trade_product)
        order.action_confirm()

        self.assertFalse(order.trade_id)

    def test_confirming_order_already_linked_to_a_trade_updates_it(self):
        """A trade picked manually before confirming must be reused, not
        replaced by a freshly auto-created one."""
        trade = self.env['trading.trade'].create({
            'trade_type': 'short',
            'product_id': self.trade_product.id,
            'quantity': 20.0,
        })
        order = self._create_order(self.trade_product, qty=10.0)
        order.trade_id = trade.id

        order.action_confirm()

        self.assertEqual(order.trade_id, trade)
        self.assertIn(order, trade.sale_order_ids)

    def test_trade_closes_once_fully_sold(self):
        trade = self.env['trading.trade'].create({
            'trade_type': 'short',
            'product_id': self.trade_product.id,
            'quantity': 10.0,
        })
        order = self._create_order(self.trade_product, qty=10.0)
        order.trade_id = trade.id

        order.action_confirm()

        self.assertEqual(trade.status, 'closed')

    def test_trade_stays_confirmed_when_only_partially_sold(self):
        trade = self.env['trading.trade'].create({
            'trade_type': 'short',
            'product_id': self.trade_product.id,
            'quantity': 100.0,
            'status': 'confirmed',
        })
        order = self._create_order(self.trade_product, qty=10.0)
        order.trade_id = trade.id

        order.action_confirm()

        self.assertEqual(trade.status, 'confirmed')


@tagged('post_install', '-at_install')
class TestPurchaseOrderTradeSync(TransactionCase):
    """Exercises purchase_order.py: confirming a purchase order auto-creates
    or updates a trade for tradeable lines."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.vendor = cls.env['res.partner'].create({'name': 'Test Vendor'})
        cls.trade_product = cls.env['product.product'].create({
            'name': 'Test Cocoa',
            'type': 'consu',
        })
        cls.non_trade_product = cls.env['product.product'].create({
            'name': 'Office Supplies',
            'type': 'consu',
            'is_tradeable': False,
        })

    def _create_po(self, product, qty=10.0, price_unit=20.0):
        return self.env['purchase.order'].create({
            'partner_id': self.vendor.id,
            'order_line': [(0, 0, {
                'product_id': product.id,
                'product_qty': qty,
                'price_unit': price_unit,
                'name': product.name,
            })],
        })

    def test_confirming_po_with_tradeable_line_creates_a_long_trade(self):
        po = self._create_po(self.trade_product, qty=50.0, price_unit=10.0)
        po.button_confirm()

        self.assertTrue(po.trade_id)
        trade = po.trade_id
        self.assertEqual(trade.trade_type, 'long')
        self.assertEqual(trade.status, 'confirmed')
        self.assertEqual(trade.product_id, self.trade_product)
        self.assertAlmostEqual(trade.quantity, 50.0, places=2)
        self.assertAlmostEqual(trade.price, 10.0, places=2)
        self.assertEqual(trade.purchase_id, po)

    def test_confirming_po_with_only_non_tradeable_lines_creates_no_trade(self):
        po = self._create_po(self.non_trade_product)
        po.button_confirm()

        self.assertFalse(po.trade_id)

    def test_confirming_po_already_linked_to_a_trade_updates_it_in_place(self):
        """A trade picked manually before confirming must be updated with
        the PO's quantity/price/currency, not replaced by a new one."""
        trade = self.env['trading.trade'].create({
            'trade_type': 'long',
            'product_id': self.trade_product.id,
            'quantity': 0.0,
            'price': 0.0,
        })
        po = self._create_po(self.trade_product, qty=30.0, price_unit=15.0)
        po.trade_id = trade.id

        po.button_confirm()

        self.assertEqual(po.trade_id, trade)
        self.assertEqual(trade.purchase_id, po)
        self.assertAlmostEqual(trade.quantity, 30.0, places=2)
        self.assertAlmostEqual(trade.price, 15.0, places=2)
