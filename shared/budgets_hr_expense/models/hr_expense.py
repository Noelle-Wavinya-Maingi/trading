# -*- coding: utf-8 -*-
from odoo import api, fields, models


class HrExpenseBudgetLine(models.Model):
    """Generic link between an expense and a budget line. Industry-agnostic: only
    needs ele_budget_line_id + total_amount_currency. Anchor-specific fields (trade_id,
    production_id, ...) and their own onchange logic live in each industry module."""
    _inherit = 'hr.expense'

    ele_budget_line_id = fields.Many2one(
        'operations.budget.line',
        string='Budget Line',
        help='Budget line to link this expense to. When linked, the actual_amount will '
             'be updated from the expense amount.',
        domain="[('expense_id', '=', False)]",
        ondelete='set null',
    )

    @api.onchange('ele_budget_line_id')
    def _onchange_budget_line_id(self):
        """Generate the expense name and payment mode from the linked budget line."""
        if self.ele_budget_line_id:
            prefix = self.ele_budget_line_id._get_display_name_prefix()
            budget_line_name = self.ele_budget_line_id.name or ''
            if prefix and budget_line_name:
                self.name = f"{prefix} / {budget_line_name}"
            elif budget_line_name:
                self.name = budget_line_name
            self.payment_mode = 'company_account'

    # === budget anchor field registry ===
    # Each industry module (omni_budget's file_id, ele_trading_budget's
    # trade_id, ...) used to hand-roll its own uniquely-named onchange to set
    # its own field from the selected budget line (e.g. _onchange_budget_line_
    # id_file / _onchange_budget_line_id_trade). Those never actually
    # collided -- Odoo supports multiple independently-named @api.onchange
    # handlers on the same field fine -- but the only thing preventing a
    # collision was the naming discipline of picking a unique suffix, the
    # same discipline that quietly broke once for order.bridge.mixin and
    # operations.budget.line, where hook methods used bare names instead of a
    # registry. Registering here instead removes that discipline requirement
    # entirely: a new vertical has no method name to collide on.
    def _budget_anchor_providers(self):
        """Return the list of registered budget-anchor providers. Base case:
        none. Override, call super()._budget_anchor_providers(), and append
        your own dict -- never replace the list, since another vertical's
        provider may also be registered on this shared model.

        Each provider is a dict:
            {
                'field': 'file_id',  # the field on hr.expense this vertical owns
                'get_from_budget_line': lambda line: ...,  # -> recordset or False
            }
        """
        return []

    @api.onchange('ele_budget_line_id')
    def _onchange_budget_line_id_anchor(self):
        """Set each registered vertical's own anchor field from the selected
        budget line, dispatched via _budget_anchor_providers() instead of one
        onchange method per vertical."""
        if not self.ele_budget_line_id:
            return
        for provider in self._budget_anchor_providers():
            value = provider['get_from_budget_line'](self.ele_budget_line_id)
            if value:
                self[provider['field']] = value

    @api.model_create_multi
    def create(self, vals_list):
        """Update the linked budget line's actual_amount when an expense is created
        already carrying a ele_budget_line_id."""
        expenses = super().create(vals_list)
        for expense in expenses:
            if expense.ele_budget_line_id and expense.total_amount_currency:
                expense._update_budget_line_amount()
        return expenses

    def write(self, vals):
        """Keep the linked budget line's actual_amount in sync, and clear the old
        budget line's expense_id when the link is moved to a different expense."""
        budget_line_changed = 'ele_budget_line_id' in vals
        amount_changed = 'total_amount_currency' in vals

        old_budget_lines = {}
        if budget_line_changed:
            for expense in self:
                old_budget_lines[expense.id] = expense.ele_budget_line_id

        result = super().write(vals)

        if budget_line_changed or amount_changed:
            for expense in self:
                if expense.ele_budget_line_id:
                    expense._update_budget_line_amount()

                old_budget_line = old_budget_lines.get(expense.id)
                if old_budget_line and old_budget_line != expense.ele_budget_line_id:
                    if old_budget_line.expense_id == expense:
                        old_budget_line.sudo().with_context(skip_expense_update=True).write({'expense_id': False})

        return result

    def _update_budget_line_amount(self):
        """Push this expense's amount onto its linked budget line."""
        self.ensure_one()
        if not self.ele_budget_line_id:
            return
        budget_line = self.ele_budget_line_id.sudo().with_context(
            skip_expense_update=True, budget_line_backend_sync=True
        )
        budget_line.write({
            'actual_amount': self.total_amount_currency or 0.0,
            'expense_id': self.id,
            'date_actual': self.date,
        })
        budget_line._notify_anchor_of_amount_change()
