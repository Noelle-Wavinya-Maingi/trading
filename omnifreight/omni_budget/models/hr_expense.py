# -*- coding: utf-8 -*-
from odoo import api, fields, models


class HrExpense(models.Model):
    """Freight-specific narrowing of the generic expense/budget-line link.

    The field itself, and all of the amount syncing between an expense and its
    budget line, come from budgets_hr_expense. This module only scopes the
    selectable lines to the expense's own manufacturing order and keeps the two
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
        domain="[('budget_id.production_id', '=', production_id), ('expense_id', '=', False)]",
    )

    @api.onchange('production_id')
    def _onchange_production_id_clear_budget_line(self):
        """Clear budget_line_id when the manufacturing order changes, since the
        previously chosen line belongs to a different order's budget."""
        if self.production_id != self._origin.production_id:
            self.budget_line_id = False

    @api.onchange('budget_line_id')
    def _onchange_budget_line_id_production(self):
        """Set production_id from the selected budget line's header. Name and
        payment_mode generation is handled generically by budgets_hr_expense."""
        if self.budget_line_id and self.budget_line_id.budget_id:
            self.production_id = self.budget_line_id.budget_id.production_id
