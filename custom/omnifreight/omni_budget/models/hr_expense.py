# -*- coding: utf-8 -*-
from odoo import api, fields, models


class HrExpense(models.Model):
    """Freight-specific narrowing of the generic expense/budget-line link.

    The field itself, and all of the amount syncing between an expense and its
    budget line, come from budgets_hr_expense. This module only scopes the
    selectable lines to the expense's own freight file and keeps the two
    sides in step in the UI.

    Note the previous implementation in omni_ops also carried its own create(),
    write() and _update_budget_line_amount(). Those duplicated budgets_hr_expense
    and, because the method name matched, actually *shadowed* the generic
    _update_budget_line_amount -- which routes through the budget line's
    _notify_anchor_of_amount_change() hook and therefore refreshes both the
    budget's actual costs and its margin display. The local copy only refreshed
    actual costs. They are dropped here so the generic implementation applies."""
    _inherit = 'hr.expense'

    budget_line_id = fields.Many2one(
        domain="[('mrp_budget_id.file_id', '=', file_id), ('expense_id', '=', False)]",
    )

    @api.onchange('file_id')
    def _onchange_file_id_clear_budget_line(self):
        """Clear budget_line_id when the freight file changes, since the
        previously chosen line belongs to a different file's budget."""
        if self.file_id != self._origin.file_id:
            self.budget_line_id = False

    @api.onchange('budget_line_id')
    def _onchange_budget_line_id_file(self):
        """Set file_id from the selected budget line's header. Name and
        payment_mode generation is handled generically by budgets_hr_expense."""
        if self.budget_line_id and self.budget_line_id.mrp_budget_id:
            self.file_id = self.budget_line_id.mrp_budget_id.file_id
