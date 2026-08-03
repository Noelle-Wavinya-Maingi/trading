# -*- coding: utf-8 -*-
from unittest.mock import patch

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestOperationsBudgetLine(TransactionCase):
    """Exercises the core operations.budget.line model standalone -- no client
    bridge module (trading_budget, omni_ops, ...) and no actualization backend
    (budgets_hr_expense) installed. Everything here must hold for `budgets` on
    its own, since that's the whole point of keeping it dependency-free."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Line = cls.env['operations.budget.line']

    def _create_line(self, **vals):
        vals.setdefault('name', 'Test line')
        vals.setdefault('line_type', 'expense')
        return self.Line.create(vals)

    # === display_type / constraints ===
    def test_section_row_is_valid_without_line_type(self):
        line = self.Line.create({'name': 'Header', 'display_type': 'line_section', 'line_type': False})
        self.assertEqual(line.display_type, 'line_section')

    def test_normal_line_requires_line_type(self):
        with self.assertRaises(ValidationError):
            self.Line.create({'name': 'x', 'line_type': False})

    def test_section_cannot_have_line_type(self):
        with self.assertRaises(ValidationError):
            self.Line.create({'name': 'x', 'display_type': 'line_section', 'line_type': 'expense'})

    def test_negative_budgeted_amount_rejected(self):
        with self.assertRaises(ValidationError):
            self._create_line(budgeted_amount=-10.0)

    def test_negative_actual_amount_rejected(self):
        with self.assertRaises(ValidationError):
            self._create_line(actual_amount=-10.0)

    def test_section_cannot_link_account_move(self):
        vendor = self.env['res.partner'].create({'name': 'Test Vendor'})
        move = self.env['account.move'].create({'move_type': 'in_invoice', 'partner_id': vendor.id})
        with self.assertRaises(ValidationError):
            self.Line.create({
                'name': 'x', 'display_type': 'line_section', 'line_type': False,
                'account_move_id': move.id,
            })

    # === computed fields ===
    def test_variance_is_actual_minus_budgeted(self):
        line = self._create_line(budgeted_amount=100.0, actual_amount=80.0)
        self.assertEqual(line.variance_amount, -20.0)

    def test_amount_company_currency_passthrough_when_same_currency(self):
        line = self._create_line(actual_amount=50.0, currency_id=self.env.company.currency_id.id)
        self.assertEqual(line.amount_company_currency, 50.0)

    def test_source_reference_reflects_linked_invoice(self):
        vendor = self.env['res.partner'].create({'name': 'Test Vendor'})
        move = self.env['account.move'].create({'move_type': 'in_invoice', 'partner_id': vendor.id})
        line = self._create_line(account_move_id=move.id)
        self.assertEqual(line.source_reference, move)

    def test_source_reference_empty_with_no_document(self):
        line = self._create_line(actual_amount=10.0)
        self.assertFalse(line.source_reference)

    # === default hooks are no-ops without any bridge/backend module ===
    def test_default_anchor_is_empty(self):
        line = self._create_line(actual_amount=10.0)
        self.assertFalse(line._get_anchor_record())

    def test_default_anchor_link_vals_is_empty_dict(self):
        line = self._create_line(actual_amount=10.0)
        self.assertEqual(line._get_anchor_link_vals(), {})

    def test_default_notify_anchor_is_noop(self):
        line = self._create_line(actual_amount=10.0)
        line._notify_anchor_of_amount_change()  # must not raise

    def test_default_sync_actual_source_is_noop(self):
        """With no actualization backend installed, changing actual_amount never
        creates any backing document -- the line just trusts the value as entered."""
        line = self._create_line(actual_amount=10.0)
        line.write({'actual_amount': 25.0})  # must not raise, nothing else to assert on

    # === anchor chatter contract (_check_anchor_supports_chatter) ===
    def test_tracking_message_posted_when_anchor_supports_chatter(self):
        partner = self.env.user.partner_id
        with patch.object(type(self.Line), '_get_anchor_record', return_value=partner):
            line = self._create_line(name='Original name', actual_amount=10.0)
            count_before = len(partner.message_ids)
            line.write({'name': 'Changed name'})
        self.assertGreater(len(partner.message_ids), count_before)

    def test_write_blocked_when_anchor_lacks_chatter(self):
        """A client overriding _get_anchor_record() to return a non-mail.thread
        record gets a clear ValidationError, not an opaque AttributeError from
        deep inside message_post()."""
        non_chatter_anchor = self.env['res.currency'].browse(self.env.company.currency_id.id)
        with patch.object(type(self.Line), '_get_anchor_record', return_value=non_chatter_anchor):
            line = self._create_line(name='Original name', actual_amount=10.0)
            with self.assertRaises(ValidationError):
                line.write({'name': 'Changed name'})
