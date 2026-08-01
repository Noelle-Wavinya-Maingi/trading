# -*- coding: utf-8 -*-
from unittest.mock import patch

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestOperationsBudgetLineExpenseActualization(TransactionCase):
    """Exercises budgets_hr_expense's _sync_actual_source() override on the bare
    core operations.budget.line -- no client bridge module (trading_budget,
    omni_ops, ...) is required to install/test this in isolation. Since the core
    model has no anchor by default, tests that need one past the "blocked without
    anchor" check patch _get_anchor_link_vals directly, standing in for what a
    client's own _inherit would normally supply."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Line = cls.env['operations.budget.line']
        cls.env['hr.employee'].create({
            'name': 'Test Employee',
            'user_id': cls.env.user.id,
        })

    def _create_line(self, **vals):
        vals.setdefault('name', 'Test line')
        vals.setdefault('line_type', 'expense')
        return self.Line.create(vals)

    def _anchored(self):
        return patch.object(
            type(self.Line), '_get_anchor_link_vals', return_value={'description': 'anchored'}
        )

    def test_zero_amount_does_not_create_expense(self):
        line = self._create_line(actual_amount=0.0)
        self.assertFalse(line.expense_id)

    def test_positive_amount_without_anchor_is_blocked(self):
        with self.assertRaises(ValidationError):
            self._create_line(actual_amount=100.0)

    def test_positive_amount_with_anchor_creates_expense(self):
        with self._anchored():
            line = self._create_line(actual_amount=150.0)
        self.assertTrue(line.expense_id)
        self.assertEqual(line.expense_id.total_amount_currency, 150.0)
        self.assertEqual(line.expense_id.budget_line_id, line)

    def test_expense_removed_when_amount_drops_to_zero(self):
        with self._anchored():
            line = self._create_line(actual_amount=150.0)
            expense = line.expense_id
            self.assertTrue(expense)
            line.write({'actual_amount': 0.0})
        self.assertFalse(line.expense_id)
        self.assertFalse(expense.exists())

    def test_expense_removed_when_invoice_linked_instead(self):
        with self._anchored():
            line = self._create_line(actual_amount=150.0)
            self.assertTrue(line.expense_id)
            vendor = self.env['res.partner'].create({'name': 'Test Vendor'})
            move = self.env['account.move'].create({
                'move_type': 'in_invoice',
                'partner_id': vendor.id,
            })
            line.write({'account_move_id': move.id})
        self.assertFalse(line.expense_id)

    def test_partner_is_carried_onto_the_expense_as_vendor(self):
        """vendor_id is a standard hr.expense field and feeds partner_id on the
        generated accounting entries, so a budget line's partner must reach it."""
        vendor = self.env['res.partner'].create({'name': 'Line Vendor'})
        with self._anchored():
            line = self._create_line(actual_amount=75.0, partner_id=vendor.id)
        self.assertEqual(line.expense_id.vendor_id, vendor)

    def test_charge_lines_never_create_expenses(self):
        with self._anchored():
            line = self._create_line(actual_amount=150.0, line_type='charge')
        self.assertFalse(line.expense_id)
