# -*- coding: utf-8 -*-
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestAccountMoveTradePnl(AccountTestInvoicingCommon):
    """Exercises account_move_trade_pnl.py: the logic that pushes a posted
    invoice/bill's amounts into a trade's additional_costs/additional_revenue
    and guards against processing the same document twice.

    Invoices are kept in the company's own currency throughout, so these
    tests are about the P&L wiring, not the currency conversion path.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # AccountTestInvoicingCommon runs as a real (non-superuser) test
        # user, unlike plain TransactionCase -- it needs an actual trading
        # group, since base.group_system no longer bypasses these ACLs.
        # Requires the security model from the trading-security-model
        # branch/PR to be installed -- merge that before/with this one.
        cls.env.user.group_ids |= cls.env.ref('trading.group_trading_manager')
        cls.trade_product = cls.env['product.product'].create({
            'name': 'Test Cocoa',
            'type': 'consu',
            'categ_id': cls.product_category.id,
        })
        cls.other_product = cls.env['product.product'].create({
            'name': 'Freight',
            'type': 'service',
            'categ_id': cls.product_category.id,
        })

    def _create_trade(self, **vals):
        base_vals = {
            'trade_type': 'long',
            'product_id': self.trade_product.id,
        }
        base_vals.update(vals)
        return self.env['trading.trade'].create(base_vals)

    def _line(self, product, price_unit, quantity=1.0):
        return self._prepare_invoice_line(
            product_id=product.id, price_unit=price_unit, quantity=quantity, tax_ids=[],
        )

    # ------------------------------------------------------------------
    # Direct bill, no purchase order involved.
    # ------------------------------------------------------------------
    def test_direct_bill_product_line_sets_quantity_and_price(self):
        """A bill for the trade's own product (no PO) should set the trade's
        quantity/price from the line, not treat it as an additional cost."""
        trade = self._create_trade()
        bill = self._create_invoice(
            move_type='in_invoice',
            trade_id=trade.id,
            invoice_line_ids=[self._line(self.trade_product, price_unit=10.0, quantity=50.0)],
            post=True,
        )
        self.assertTrue(bill.trade_pnl_processed)
        self.assertAlmostEqual(trade.quantity, 50.0, places=2)
        self.assertAlmostEqual(trade.price, 10.0, places=2)
        self.assertAlmostEqual(trade.additional_costs, 0.0, places=2)

    def test_direct_bill_non_product_line_is_additional_cost(self):
        """A line for anything other than the trade's own product (e.g.
        freight) is a cost on top of the trade, not part of its quantity."""
        trade = self._create_trade(quantity=50.0, price=10.0)
        self._create_invoice(
            move_type='in_invoice',
            trade_id=trade.id,
            invoice_line_ids=[self._line(self.other_product, price_unit=75.0)],
            post=True,
        )
        self.assertAlmostEqual(trade.additional_costs, 75.0, places=2)
        # The trade's own quantity/price are untouched by a costs-only bill.
        self.assertAlmostEqual(trade.quantity, 50.0, places=2)

    # ------------------------------------------------------------------
    # Direct customer invoice, no sale order involved.
    # ------------------------------------------------------------------
    def test_direct_invoice_adds_additional_revenue(self):
        trade = self._create_trade()
        invoice = self._create_invoice(
            move_type='out_invoice',
            trade_id=trade.id,
            invoice_line_ids=[self._line(self.other_product, price_unit=120.0)],
            post=True,
        )
        self.assertTrue(invoice.trade_pnl_processed)
        self.assertAlmostEqual(trade.additional_revenue, 120.0, places=2)

    def test_reposting_same_invoice_does_not_double_count(self):
        """trade_pnl_processed is the guard against a document being applied
        to the trade twice -- e.g. if action_post() logic ever runs again."""
        trade = self._create_trade()
        invoice = self._create_invoice(
            move_type='out_invoice',
            trade_id=trade.id,
            invoice_line_ids=[self._line(self.other_product, price_unit=120.0)],
            post=True,
        )
        self.assertAlmostEqual(trade.additional_revenue, 120.0, places=2)

        # Calling the update again should be a no-op: the guard is what
        # keeps a re-triggered write/post from adding 120 a second time.
        invoice._update_trade_pnl_from_invoice()
        self.assertAlmostEqual(trade.additional_revenue, 120.0, places=2)

    # ------------------------------------------------------------------
    # Purchase-order-linked bill: the trade's own product line is skipped
    # (already handled by PO confirmation), everything else is a cost.
    # ------------------------------------------------------------------
    def test_po_linked_bill_skips_trade_product_line(self):
        trade = self._create_trade(quantity=50.0, price=10.0)
        po = self.env['purchase.order'].create({
            'partner_id': self.partner_a.id,
            'trade_id': trade.id,
        })
        bill = self._create_invoice(
            move_type='in_invoice',
            invoice_origin=po.name,
            invoice_line_ids=[
                self._line(self.trade_product, price_unit=10.0, quantity=50.0),
                self._line(self.other_product, price_unit=25.0),
            ],
            post=True,
        )
        self.assertEqual(bill.trade_id, trade)
        self.assertAlmostEqual(trade.additional_costs, 25.0, places=2)
        # Trade's own quantity/price came from PO confirmation, not this bill.
        self.assertAlmostEqual(trade.quantity, 50.0, places=2)

    # ------------------------------------------------------------------
    # Line-level trades: no header trade_id, individual lines carry their
    # own trade_id (e.g. a shared vendor bill covering several trades).
    #
    # _process_line_level_trades() groups lines by trade_id and is meant to
    # handle several distinct trades on one document -- but neither normal
    # entry point actually reaches it in that case:
    #   - action_post() only calls it when the move still has no header
    #     trade_id, and write()'s own posting handler (in
    #     account_move_lifecycle.py) always collapses a headerless move's
    #     lines to line_trades[0] and takes the single-trade path first,
    #     inside the very same write() that puts the move in 'posted' state.
    #   - create() calls it too, but only a move already in 'posted' state
    #     would make it past the `state != 'posted'` guard, and Odoo core
    #     itself refuses to create a move directly in 'posted' state.
    # So the multi-trade grouping this method exists for is dead code on
    # every supported path today. These tests call it directly (after
    # forcing state via a raw UPDATE, bypassing the write() override that
    # would otherwise collapse it first) to pin its behaviour in isolation.
    # ------------------------------------------------------------------
    def _force_posted(self, move):
        move.env.cr.execute("UPDATE account_move SET state = 'posted' WHERE id = %s", (move.id,))
        move.invalidate_recordset(['state'])

    def test_line_level_vendor_bill_adds_additional_costs_per_trade(self):
        trade_a = self._create_trade()
        trade_b = self._create_trade()
        bill = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2026-01-01',
            'invoice_line_ids': [
                (0, 0, {
                    'product_id': self.other_product.id,
                    'price_unit': 40.0,
                    'quantity': 1.0,
                    'tax_ids': [],
                    'trade_id': trade_a.id,
                }),
                (0, 0, {
                    'product_id': self.other_product.id,
                    'price_unit': 15.0,
                    'quantity': 1.0,
                    'tax_ids': [],
                    'trade_id': trade_b.id,
                }),
            ],
        })
        self._force_posted(bill)
        bill._process_line_level_trades()

        self.assertAlmostEqual(trade_a.additional_costs, 40.0, places=2)
        self.assertAlmostEqual(trade_b.additional_costs, 15.0, places=2)
        self.assertTrue(bill.trade_pnl_processed)

    def test_line_level_customer_invoice_adds_additional_revenue_per_trade(self):
        """Same as the vendor-bill case above, but for a customer invoice --
        covers the sibling branch in _process_line_level_trades."""
        trade_a = self._create_trade()
        trade_b = self._create_trade()
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2026-01-01',
            'invoice_line_ids': [
                (0, 0, {
                    'product_id': self.other_product.id,
                    'price_unit': 60.0,
                    'quantity': 1.0,
                    'tax_ids': [],
                    'trade_id': trade_a.id,
                }),
                (0, 0, {
                    'product_id': self.other_product.id,
                    'price_unit': 20.0,
                    'quantity': 1.0,
                    'tax_ids': [],
                    'trade_id': trade_b.id,
                }),
            ],
        })
        self._force_posted(invoice)
        invoice._process_line_level_trades()

        self.assertAlmostEqual(trade_a.additional_revenue, 60.0, places=2)
        self.assertAlmostEqual(trade_b.additional_revenue, 20.0, places=2)
