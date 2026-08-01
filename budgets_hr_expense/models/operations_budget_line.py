# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class OperationsBudgetLineHrExpense(models.Model):
    """hr.expense actualization backend for the shared operations.budget.line: a
    cost-side line with a positive actual amount and no linked invoice/bill
    auto-creates a backing hr.expense, undone if the amount drops to zero or a
    document gets linked instead. This is one possible way to realize a line's
    actual_amount -- the core `budgets` module has no dependency on hr.expense and
    knows nothing about this mechanism; it only calls the generic
    `_sync_actual_source()` hook this module overrides."""
    _inherit = 'operations.budget.line'

    expense_id = fields.Many2one(
        'hr.expense',
        string='Expense',
        tracking=True,
        help='Expense record linked to this budget line. Can be created automatically or linked manually.',
        ondelete='set null'
    )
    expense_is_submitted = fields.Boolean(
        'Expense Submitted',
        compute='_compute_expense_is_submitted',
        store=False,
        help='True if the linked expense has been submitted'
    )

    source_reference = fields.Reference(
        selection_add=[('hr.expense', 'Expense')],
    )

    @api.depends('expense_id')
    def _compute_source_reference(self):
        """Extend the core account.move-only computation with the expense fallback."""
        super()._compute_source_reference()
        for line in self:
            if not line.source_reference and line.expense_id:
                line.source_reference = f'hr.expense,{line.expense_id.id}'

    @api.depends('expense_id', 'expense_id.state')
    def _compute_expense_is_submitted(self):
        """Compute whether the linked expense is submitted/approved/done.

        Odoo 19 removed hr.expense.sheet entirely — expenses are approved
        individually now (auto-validated if the employee has no manager set),
        so this only needs the expense's own state, not a separate sheet.
        """
        for line in self:
            line.expense_is_submitted = bool(line.expense_id) and line.expense_id.state in ('submitted', 'approved', 'done')

    @api.onchange('display_type')
    def _onchange_display_type(self):
        super()._onchange_display_type()
        if self.display_type:
            self.expense_id = False

    @api.constrains('display_type', 'expense_id')
    def _check_no_expense_on_section(self):
        """A section/note can never be linked to an expense."""
        for line in self:
            if line.display_type and line.expense_id:
                raise ValidationError(_("A Section/Note line cannot be linked to an Expense."))

    def _should_create_expense(self):
        """Only cost-side lines with no already-linked invoice/bill auto-create an
        expense. Revenue ('charge') lines never do — an expense represents outflow.
        Section/note rows never do either — they carry no real amount."""
        self.ensure_one()
        return (
            not self.display_type and
            self.line_type in ('expense', 'other') and
            not self.account_move_id and
            self.actual_amount and self.actual_amount > 0 and
            not self.expense_id
        )

    def _should_unlink_expense(self):
        """An expense should be dropped if the line no longer has a positive actual
        amount, or is now covered by a linked invoice/bill instead."""
        self.ensure_one()
        return bool(self.expense_id) and (
            self.account_move_id or not self.actual_amount or self.actual_amount <= 0
        )

    def _create_expense_from_budget_line(self):
        """Create or update the hr.expense record backing this budget line."""
        self.ensure_one()

        if not self._should_create_expense() and not self.expense_id:
            return False
        if not self.actual_amount or self.actual_amount <= 0:
            return False

        employee = self.env.user.employee_id
        if not employee:
            raise ValidationError(_(
                "Cannot create expense: User '%s' has no associated employee record. "
                "Please create an employee record for this user."
            ) % self.env.user.name)

        anchor_vals = self._get_anchor_link_vals()
        if not anchor_vals:
            raise ValidationError(_(
                "Cannot create expense: Budget line '%s' is not linked to a parent record."
            ) % self.name)

        expense_name = self.name or _('Expense from Budget Line')
        prefix = self._get_display_name_prefix()
        formatted_name = f"{prefix} / {expense_name}" if prefix else expense_name

        expense_vals = {
            'name': formatted_name,
            'employee_id': employee.id,
            'product_id': self.product_id.id if self.product_id else False,
            'total_amount_currency': self.actual_amount,
            'currency_id': self.currency_id.id,
            'date': self.date_actual or fields.Date.today(),
            'company_id': self._get_conversion_company().id,
            'payment_mode': 'company_account',
            'budget_line_id': self.id,
            'description': self.description or '',
            **anchor_vals,
        }

        if self.expense_id:
            self.expense_id.write(expense_vals)
            return self.expense_id
        return self.env['hr.expense'].create(expense_vals)

    def _create_expense_for_line(self):
        """Create expense for this line, handling errors gracefully."""
        self.ensure_one()
        try:
            expense = self._create_expense_from_budget_line()
            if expense:
                self.sudo().write({'expense_id': expense.id})
        except ValidationError:
            raise
        except Exception as e:
            _logger.warning("Failed to create expense for budget line %s: %s", self.id, str(e))

    def _unlink_expense_for_line(self):
        """Unlink (and remove) the expense currently backing this line."""
        self.ensure_one()
        expense_to_unlink = self.expense_id
        self.sudo().write({'expense_id': False})
        if expense_to_unlink.budget_line_id == self:
            expense_to_unlink.write({'budget_line_id': False})
        expense_to_unlink.unlink()

    def _sync_actual_source(self):
        """Create, update, or unlink the backing hr.expense based on the current
        state of the line. Overrides the core no-op hook."""
        if self._context.get('skip_expense_update'):
            return
        if self._should_create_expense():
            self._create_expense_for_line()
        elif self._should_unlink_expense():
            self._unlink_expense_for_line()

    def write(self, vals):
        result = super().write(vals)
        if 'expense_id' in vals:
            for line in self:
                if line.expense_id and not line._context.get('skip_expense_update'):
                    expense_vals = {'budget_line_id': line.id}
                    line.expense_id.write(expense_vals)
                    if not line.actual_amount and line.expense_id.total_amount_currency:
                        line.actual_amount = line.expense_id.total_amount_currency
        return result
