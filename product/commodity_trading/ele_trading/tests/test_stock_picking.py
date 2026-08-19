# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestStockPicking(TransactionCase):
    """Exercises stock_picking.py: linking received lots to a PO-backed
    trade, and recomputing/closing a trade on delivery.

    Both hooks are called directly rather than through button_validate() --
    they take an explicit `picking` argument independent of the recordset
    they're called on, and driving the full stock reservation/validation
    state machine would test Odoo's own stock module more than ours."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.vendor = cls.env['res.partner'].create({'name': 'Test Vendor'})
        cls.customer = cls.env['res.partner'].create({'name': 'Test Customer'})
        cls.tracked_product = cls.env['product.product'].create({
            'name': 'Test Cocoa',
            'type': 'consu',
            'is_storable': True,
            'tracking': 'lot',
        })

    def test_incoming_receipt_links_lot_to_trade(self):
        po = self.env['purchase.order'].create({
            'partner_id': self.vendor.id,
            'order_line': [(0, 0, {
                'product_id': self.tracked_product.id,
                'product_qty': 10.0,
                'price_unit': 5.0,
                'name': self.tracked_product.name,
            })],
        })
        po.button_confirm()
        trade = po.ele_trade_id
        self.assertTrue(trade)

        picking = po.picking_ids[:1]
        self.assertTrue(picking)
        lot = self.env['stock.lot'].create({
            'name': 'LOT-TEST-1',
            'product_id': self.tracked_product.id,
        })
        picking.move_line_ids.write({'lot_id': lot.id, 'quantity': 10.0})

        picking._process_incoming_picking(picking)

        self.assertIn(lot, trade.lot_ids)

    def test_incoming_receipt_with_no_matching_trade_does_not_error(self):
        """A receipt for a PO with no trade (e.g. a non-tradeable product)
        must be a safe no-op, not an error."""
        po = self.env['purchase.order'].create({
            'partner_id': self.vendor.id,
            'order_line': [(0, 0, {
                'product_id': self.tracked_product.id,
                'product_qty': 5.0,
                'price_unit': 5.0,
                'name': self.tracked_product.name,
            })],
        })
        # Confirm without ever letting our own auto-trade-creation run, by
        # removing the trade it would have created -- isolates "no trade
        # found for this PO" from "trade creation is broken".
        po.button_confirm()
        po.ele_trade_id.unlink()

        picking = po.picking_ids[:1]
        picking._process_incoming_picking(picking)  # must not raise

    def test_outgoing_delivery_closes_trade_once_fully_open_position_cleared(self):
        """This close-check turns out to be structurally redundant in the
        exact-match case: sale_order.py's own action_confirm() closes the
        trade on the same "fully sold" condition, and _process_outgoing_
        picking() itself calls _compute_all_trade_fields() before reaching
        its own check -- which runs trading_trade_pnl.py's _compute_pnl(),
        carrying its *own* independent auto-close on `is_fully_matched`
        (an exact quantity match). Both of those fire first and would mask
        whether this method's own check does anything at all.

        To actually isolate it, this test builds an *oversold* position
        (sold more than purchased) without ever calling the sale order's
        overridden action_confirm(): `is_fully_matched` requires an exact
        match, so it stays False and neither of the other two mechanisms
        fires -- only open_position_quantity <= 0 (this method's own check,
        satisfied by an oversold position too) can close it."""
        po = self.env['purchase.order'].create({'partner_id': self.vendor.id})
        trade = self.env['trading.trade'].create({
            'trade_type': 'long',
            'product_id': self.tracked_product.id,
            'quantity': 10.0,
            'price': 5.0,
            'status': 'confirmed',
            'purchase_id': po.id,
        })
        so = self.env['sale.order'].create({
            'partner_id': self.customer.id,
            'order_line': [(0, 0, {
                'product_id': self.tracked_product.id,
                'product_uom_qty': 15.0,
                'price_unit': 8.0,
            })],
        })
        # Simulate "confirmed" without going through our own action_confirm()
        # override, whose auto-create/auto-close side effects would
        # otherwise make it impossible to isolate this method's own check.
        so.write({'state': 'sale', 'ele_trade_id': trade.id})
        trade.write({'sale_order_ids': [(4, so.id)]})

        self.assertFalse(trade.is_fully_matched)
        self.assertLessEqual(trade.open_position_quantity, 0.0)
        self.assertEqual(trade.status, 'confirmed')

        wh = self.env['stock.warehouse'].search([], limit=1)
        picking = self.env['stock.picking'].create({
            'sale_id': so.id,
            'picking_type_id': wh.out_type_id.id,
            'location_id': wh.out_type_id.default_location_src_id.id,
            'location_dest_id': wh.out_type_id.default_location_dest_id.id,
        })
        self.assertEqual(picking.ele_trade_id, trade)

        picking._process_outgoing_picking(picking)

        self.assertEqual(trade.status, 'closed')

    def test_outgoing_delivery_leaves_trade_open_with_remaining_position(self):
        trade = self.env['trading.trade'].create({
            'trade_type': 'long',
            'product_id': self.tracked_product.id,
            'quantity': 100.0,
            'price': 5.0,
            'status': 'confirmed',
            # open_position_quantity only reads as a long position once a
            # purchase document actually backs the quantity (see
            # trading_trade_pnl.py's _compute_position) -- a bare `quantity`
            # with no purchase_id reads as an unbacked short instead.
            'purchase_id': self.env['purchase.order'].create({
                'partner_id': self.vendor.id,
            }).id,
        })
        so = self.env['sale.order'].create({
            'partner_id': self.customer.id,
            'ele_trade_id': trade.id,
            'order_line': [(0, 0, {
                'product_id': self.tracked_product.id,
                'product_uom_qty': 10.0,
                'price_unit': 8.0,
            })],
        })
        so.action_confirm()
        self.assertGreater(trade.open_position_quantity, 0.0)

        picking = so.picking_ids[:1]
        picking._process_outgoing_picking(picking)

        self.assertEqual(trade.status, 'confirmed')
