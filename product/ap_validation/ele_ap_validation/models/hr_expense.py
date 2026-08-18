# -*- coding: utf-8 -*-
from odoo import api, models, fields


class HrExpense(models.Model):
    """The bill-matching half of hr.expense: an expense raised for a vendor bill
    carries that bill's reference, and approving the expense validates the bill.

    This was previously tangled together with freight (production_id/file_number)
    and budgeting (budget_line_id) concerns in one file; each now lives with the
    module that owns it."""
    _inherit = 'hr.expense'

    ele_bill_reference = fields.Char(string='Bill Reference')

    def write(self, vals):
        result = super().write(vals)
        # In Odoo 19 hr.expense.sheet no longer exists and approval lives directly
        # on hr.expense via approval_state, not a separate 'state' write.
        if vals.get('approval_state') == 'approved':
            self._validate_linked_bill()
        return result

    def action_post(self):
        """Company-account expenses must NOT get an auto-generated payment/move
        from Odoo's standard _create_company_paid_moves(): the real accounting
        record for those is the separately-linked vendor bill, matched via
        ele_bill_reference. Employee-paid (own_account) expenses keep the standard
        Odoo 19 wizard flow."""
        company_expenses = self.filtered(lambda e: e.payment_mode == 'company_account')
        employee_expenses = self - company_expenses

        # Company-paid: skip Odoo's own move/payment creation entirely.
        # approval_state is already 'approved' (set via _do_approve), and the
        # linked vendor bill is validated separately — nothing else to do here.
        if company_expenses:
            company_expenses._validate_linked_bill()

        if employee_expenses:
            return super(HrExpense, employee_expenses).action_post()

        return True

    def _validate_linked_bill(self):
        """Find and validate the bill linked to this expense via ele_bill_reference."""
        for expense in self:
            if expense.payment_mode != 'company_account':
                continue

            if not expense.ele_bill_reference:
                continue

            bill = self.env['account.move'].search([
                '|',
                ('ref', '=', expense.ele_bill_reference),
                ('name', '=', expense.ele_bill_reference),
                ('move_type', '=', 'in_invoice'),
                ('company_id', '=', expense.company_id.id),
            ], limit=1)

            if not bill:
                expense.message_post(body="⚠️ No bill found for reference: %s" % expense.ele_bill_reference)
                continue

            if bill.status == 'awaiting_validation':
                bill._validate_from_expense_approval()
                expense.message_post(body="✅ Linked vendor bill %s has been validated." % (bill.ref or bill.name))
            else:
                expense.message_post(body="ℹ️ Bill %s status is %s — no update needed." % (bill.ref or bill.name, bill.status))
