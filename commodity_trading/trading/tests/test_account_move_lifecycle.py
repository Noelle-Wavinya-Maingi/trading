# -*- coding: utf-8 -*-
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestAccountMoveLifecycle(AccountTestInvoicingCommon):
    """Exercises account_move_lifecycle.py: propagating trade_id onto a new
    invoice/bill from its source document, and reversing a document's P&L
    contribution when it's reset to draft or re-pointed at another trade."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
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
    # Propagation onto a newly created invoice/bill.
    # ------------------------------------------------------------------
    def test_create_propagates_trade_from_purchase_order_origin(self):
        trade = self._create_trade()
        po = self.env['purchase.order'].create({
            'partner_id': self.partner_a.id,
            'trade_id': trade.id,
        })
        bill = self._create_invoice(
            move_type='in_invoice',
            invoice_origin=po.name,
            invoice_line_ids=[self._line(self.other_product, price_unit=10.0)],
        )
        self.assertEqual(bill.trade_id, trade)

    def test_create_propagates_trade_from_sale_order_origin(self):
        trade = self._create_trade()
        so = self.env['sale.order'].sudo().create({
            'partner_id': self.partner_a.id,
            'trade_id': trade.id,
        })
        invoice = self._create_invoice(
            move_type='out_invoice',
            invoice_origin=so.name,
            invoice_line_ids=[self._line(self.other_product, price_unit=10.0)],
        )
        self.assertEqual(invoice.trade_id, trade)

    def test_create_does_not_overwrite_an_explicit_trade_id(self):
        """If the caller already picked a trade, propagation from the
        source document must not clobber that choice."""
        trade = self._create_trade()
        other_trade = self._create_trade()
        so = self.env['sale.order'].sudo().create({
            'partner_id': self.partner_a.id,
            'trade_id': other_trade.id,
        })
        invoice = self._create_invoice(
            move_type='out_invoice',
            invoice_origin=so.name,
            trade_id=trade.id,
            invoice_line_ids=[self._line(self.other_product, price_unit=10.0)],
        )
        self.assertEqual(invoice.trade_id, trade)

    # ------------------------------------------------------------------
    # Reversal on button_draft().
    # ------------------------------------------------------------------
    def test_button_draft_reverses_revenue_contribution(self):
        trade = self._create_trade()
        invoice = self._create_invoice(
            move_type='out_invoice',
            trade_id=trade.id,
            invoice_line_ids=[self._line(self.other_product, price_unit=90.0)],
            post=True,
        )
        self.assertAlmostEqual(trade.additional_revenue, 90.0, places=2)
        self.assertTrue(invoice.trade_pnl_processed)

        invoice.button_draft()

        self.assertAlmostEqual(trade.additional_revenue, 0.0, places=2)
        self.assertFalse(invoice.trade_pnl_processed)

    def test_button_draft_never_takes_revenue_below_zero(self):
        """Two invoices contribute to the same trade; resetting one to draft
        must not drag the other's contribution down with it."""
        trade = self._create_trade()
        invoice_a = self._create_invoice(
            move_type='out_invoice',
            trade_id=trade.id,
            invoice_line_ids=[self._line(self.other_product, price_unit=90.0)],
            post=True,
        )
        self._create_invoice(
            move_type='out_invoice',
            trade_id=trade.id,
            invoice_line_ids=[self._line(self.other_product, price_unit=40.0)],
            post=True,
        )
        self.assertAlmostEqual(trade.additional_revenue, 130.0, places=2)

        invoice_a.button_draft()

        # Only invoice_a's 90 comes back off; invoice_b's 40 stands.
        self.assertAlmostEqual(trade.additional_revenue, 40.0, places=2)

    # ------------------------------------------------------------------
    # Re-pointing an already-posted move at a different trade.
    # ------------------------------------------------------------------
    def test_write_trade_id_change_moves_contribution_between_trades(self):
        trade_a = self._create_trade()
        trade_b = self._create_trade()
        invoice = self._create_invoice(
            move_type='out_invoice',
            trade_id=trade_a.id,
            invoice_line_ids=[self._line(self.other_product, price_unit=55.0)],
            post=True,
        )
        self.assertAlmostEqual(trade_a.additional_revenue, 55.0, places=2)

        invoice.write({'trade_id': trade_b.id})

        self.assertAlmostEqual(trade_a.additional_revenue, 0.0, places=2)
        self.assertAlmostEqual(trade_b.additional_revenue, 55.0, places=2)
