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
        # Stands in for the anchor FK a client bridge would supply (trade_id,
        # production_id, ...). It only has to be a real hr.expense field that
        # _create_expense_from_budget_line() does not set itself -- 'description'
        # would silently overwrite a value the method computes.
        return patch.object(
            type(self.Line), '_get_anchor_link_vals', return_value={'quantity': 1}
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
        self.assertEqual(line.expense_id.ele_budget_line_id, line)

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

    def test_expense_amount_correction_resyncs_after_line_is_done(self):
        """Regression: correcting an already-synced expense's amount must keep
        re-pushing it onto the (done) budget line's actual_amount, exactly like it
        did before the done-lock was introduced. _update_budget_line_amount() runs
        on every expense write, not just the first, so the lock's exemption for
        this backend path can't be value-based (actual_amount already being
        non-zero) -- it has to hold regardless of the current value. See
        docs/TESTING.md for pre-fix failure verification (commit 0308080)."""
        with self._anchored():
            line = self._create_line(actual_amount=150.0)
        expense = line.expense_id
        self.assertEqual(line.actual_amount, 150.0)

        line.write({'state': 'done'})
        expense.write({'total_amount_currency': 175.0})

        self.assertEqual(line.actual_amount, 175.0)

    def test_forged_context_cannot_change_completed_amount(self):
        with self._anchored():
            line = self._create_line(actual_amount=150.0)
        line.write({'state': 'done'})
        with self.assertRaises(ValidationError):
            line.with_context(budget_line_backend_sync=True).write({'actual_amount': 999.0})

    def test_second_expense_correction_resyncs_completed_line(self):
        with self._anchored():
            line = self._create_line(actual_amount=150.0)
        line.write({'state': 'done'})
        line.expense_id.write({'total_amount_currency': 175.0})
        line.expense_id.write({'total_amount_currency': 180.0})
        self.assertEqual(line.actual_amount, 180.0)

    def test_expense_sync_does_not_bypass_budget_company_access(self):
        from odoo.exceptions import AccessError
        from odoo.tests.common import new_test_user

        other_company = self.env['res.company'].create({'name': 'Other expense company'})
        other_line = self.Line.with_company(other_company).create({'name': 'Other company cost'})
        employee_user = new_test_user(
            self.env, login='expense_budget_user', groups='base.group_user',
            company_id=self.env.company.id, company_ids=[(6, 0, [self.env.company.id])],
        )
        employee = self.env['hr.employee'].create({
            'name': 'Expense user', 'user_id': employee_user.id, 'company_id': self.env.company.id,
        })
        expense = self.env['hr.expense'].create({
            'name': 'Own expense', 'employee_id': employee.id,
            'total_amount_currency': 20.0,
        })
        with self.assertRaises(AccessError), self.cr.savepoint():
            expense.with_user(employee_user).with_context(
                allowed_company_ids=[self.env.company.id],
            ).write({'ele_budget_line_id': other_line.id})
        self.assertFalse(other_line.expense_id)

    def test_ordinary_employee_can_correct_own_expense_after_completion(self):
        from odoo.tests.common import new_test_user

        user = new_test_user(
            self.env, login='own_expense_budget_user', groups='base.group_user',
            company_id=self.env.company.id, company_ids=[(6, 0, [self.env.company.id])],
        )
        employee = self.env['hr.employee'].create({'name': 'Own expense user', 'user_id': user.id})
        line = self.Line.with_user(user).create({
            'name': 'Own completed line', 'line_type': 'charge', 'actual_amount': 20, 'state': 'done',
        })
        expense = self.env['hr.expense'].with_user(user).create({
            'name': 'Own correction', 'employee_id': employee.id,
            'total_amount_currency': 20, 'ele_budget_line_id': line.id,
        })
        expense.write({'total_amount_currency': 25})
        expense.write({'total_amount_currency': 30})
        self.assertEqual(line.actual_amount, 30)
