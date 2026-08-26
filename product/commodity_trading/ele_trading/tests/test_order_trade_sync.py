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
            'ele_is_tradeable': False,
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
        """A brand-new order confirmed with no purchase leg is, by definition,
        already fully sold with nothing left open -- so the newly-created
        trade closes in this same action_confirm() call via
        trading.trade._auto_close_if_fully_matched()'s short-trade branch,
        not just the 'ele_is_fully_matched' (long-trade) condition."""
        order = self._create_order(self.trade_product, qty=10.0, price_unit=100.0)
        order.action_confirm()

        self.assertTrue(order.ele_trade_id)
        trade = order.ele_trade_id
        self.assertEqual(trade.ele_trade_type, 'short')
        self.assertEqual(trade.ele_status, 'closed')
        self.assertEqual(trade.product_id, self.trade_product)
        self.assertAlmostEqual(trade.quantity, 10.0, places=2)
        self.assertAlmostEqual(trade.ele_sales_price, 100.0, places=2)
        self.assertIn(order, trade.ele_sale_order_ids)

    def test_confirming_order_with_only_non_tradeable_lines_creates_no_trade(self):
        order = self._create_order(self.non_trade_product)
        order.action_confirm()

        self.assertFalse(order.ele_trade_id)

    def test_confirming_order_already_linked_to_a_trade_updates_it(self):
        """A trade picked manually before confirming must be reused, not
        replaced by a freshly auto-created one."""
        trade = self.env['trading.trade'].create({
            'ele_trade_type': 'short',
            'product_id': self.trade_product.id,
            'quantity': 20.0,
        })
        order = self._create_order(self.trade_product, qty=10.0)
        order.ele_trade_id = trade.id

        order.action_confirm()

        self.assertEqual(order.ele_trade_id, trade)
        self.assertIn(order, trade.ele_sale_order_ids)

    def test_trade_closes_once_fully_sold_and_matched(self):
        """Closing now goes entirely through trading.trade._auto_close_if_fully_matched(),
        which trusts ele_is_fully_matched -- and that requires a purchase leg as well as
        a matching sale, not just "sold quantity == trade.quantity" on its own. A pure
        short trade with no purchase_id never reads as fully matched, so one is added here."""
        vendor = self.env['res.partner'].create({'name': 'Test Vendor'})
        po = self.env['purchase.order'].create({'partner_id': vendor.id})
        trade = self.env['trading.trade'].create({
            'ele_trade_type': 'short',
            'product_id': self.trade_product.id,
            'quantity': 10.0,
            'ele_purchase_id': po.id,
            'ele_status': 'confirmed',
        })
        order = self._create_order(self.trade_product, qty=10.0)
        order.ele_trade_id = trade.id

        order.action_confirm()

        self.assertEqual(trade.ele_status, 'closed')

    def test_short_trade_with_no_purchase_leg_closes_once_fully_sold(self):
        """Regression: a genuine short trade (no purchase leg, by design --
        see sale_order.py's _trading_sale_bridge_vals) can never read as
        ele_is_fully_matched (it requires a purchase leg), so
        _auto_close_if_fully_matched() must also recognize "short trade, no
        purchase leg, sold quantity >= quantity" on its own, mirroring the
        old sale_order.py-only closing logic. See docs/TESTING.md for
        pre-fix failure verification (commit 0308080)."""
        trade = self.env['trading.trade'].create({
            'ele_trade_type': 'short',
            'product_id': self.trade_product.id,
            'quantity': 10.0,
            'ele_status': 'confirmed',
        })
        self.assertFalse(trade.ele_purchase_id)
        order = self._create_order(self.trade_product, qty=10.0)
        order.ele_trade_id = trade.id

        order.action_confirm()

        self.assertFalse(trade.ele_is_fully_matched)
        self.assertEqual(trade.ele_status, 'closed')

    def test_new_order_fully_selling_a_short_line_creates_and_closes_trade_in_one_confirm(self):
        """The create path (trade auto-created by this very action_confirm
        call, no pre-existing ele_trade_id) must also get its closure
        checked, not just the update path -- a brand-new order that fully
        sells a tradeable line in one confirm is the common short-trade
        case. See docs/TESTING.md for pre-fix failure verification
        (commit 0308080)."""
        order = self._create_order(self.trade_product, qty=10.0, price_unit=100.0)
        self.assertFalse(order.ele_trade_id)

        order.action_confirm()

        self.assertTrue(order.ele_trade_id)
        trade = order.ele_trade_id
        self.assertEqual(trade.ele_trade_type, 'short')
        self.assertFalse(trade.ele_is_fully_matched)
        self.assertEqual(trade.ele_status, 'closed')

    def test_trade_stays_confirmed_when_only_partially_sold(self):
        trade = self.env['trading.trade'].create({
            'ele_trade_type': 'short',
            'product_id': self.trade_product.id,
            'quantity': 100.0,
            'ele_status': 'confirmed',
        })
        order = self._create_order(self.trade_product, qty=10.0)
        order.ele_trade_id = trade.id

        order.action_confirm()

        self.assertEqual(trade.ele_status, 'confirmed')


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
            'ele_is_tradeable': False,
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

        self.assertTrue(po.ele_trade_id)
        trade = po.ele_trade_id
        self.assertEqual(trade.ele_trade_type, 'long')
        self.assertEqual(trade.ele_status, 'confirmed')
        self.assertEqual(trade.product_id, self.trade_product)
        self.assertAlmostEqual(trade.quantity, 50.0, places=2)
        self.assertAlmostEqual(trade.price, 10.0, places=2)
        self.assertEqual(trade.ele_purchase_id, po)

    def test_confirming_po_with_only_non_tradeable_lines_creates_no_trade(self):
        po = self._create_po(self.non_trade_product)
        po.button_confirm()

        self.assertFalse(po.ele_trade_id)

    def test_confirming_po_already_linked_to_a_trade_updates_it_in_place(self):
        """A trade picked manually before confirming must be updated with
        the PO's quantity/price/currency, not replaced by a new one."""
        trade = self.env['trading.trade'].create({
            'ele_trade_type': 'long',
            'product_id': self.trade_product.id,
            'quantity': 0.0,
            'price': 0.0,
        })
        po = self._create_po(self.trade_product, qty=30.0, price_unit=15.0)
        po.ele_trade_id = trade.id

        po.button_confirm()

        self.assertEqual(po.ele_trade_id, trade)
        self.assertEqual(trade.ele_purchase_id, po)
        self.assertAlmostEqual(trade.quantity, 30.0, places=2)
        self.assertAlmostEqual(trade.price, 15.0, places=2)
