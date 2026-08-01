# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class OmniHrExpense(models.Model):
    """Extend hr.expense to link with manufacturing orders and budget lines."""
    _inherit = 'hr.expense'

    # === OPERATIONS MODULE FIELDS ===
    production_id = fields.Many2one(
        'mrp.production',
        string='Manufacturing Order / File Number',
        help='Manufacturing order (file number) this expense is related to',
        tracking=True,
        index=True,
    )
    # budget_line_id itself is defined generically by the budgets_hr_expense
    # module's hr.expense extension — only the freight-specific domain narrowing
    # is overridden here.
    budget_line_id = fields.Many2one(
        domain="[('budget_id.production_id', '=', production_id), ('expense_id', '=', False)]",
    )
    file_number = fields.Char(
        string='File Number',
        related='production_id.name',
        store=True,
        readonly=True,
        help='File number from the manufacturing order',
    )

    # === ONCHANGE METHODS ===
    @api.onchange('production_id')
    def _onchange_production_id(self):
        """Clear budget_line_id when production_id changes."""
        if self.production_id != self._origin.production_id:
            self.budget_line_id = False

    @api.onchange('budget_line_id')
    def _onchange_budget_line_id_production(self):
        """Set production_id from the selected budget line's header. Name/payment_mode
        generation is handled generically by operations' own onchange on this field."""
        if self.budget_line_id and self.budget_line_id.budget_id:
            self.production_id = self.budget_line_id.budget_id.production_id

    # === METHODS ===
    @api.model_create_multi
    def create(self, vals_list):
        """Override create to update budget line actual_amount when expense is created with budget_line_id."""
        expenses = super().create(vals_list)

        # Update budget line for expenses created with budget_line_id and amount
        for expense in expenses:
            if expense.budget_line_id and expense.total_amount_currency:
                expense._update_budget_line_amount()

        return expenses

    def write(self, vals):
        """Override write to update budget line actual_amount when expense is linked."""
        # Track if budget_line_id or total_amount_currency is being changed
        budget_line_changed = 'budget_line_id' in vals
        amount_changed = 'total_amount_currency' in vals

        # Get old budget_line_id before write
        old_budget_line_ids = {}
        if budget_line_changed:
            for expense in self:
                old_budget_line_ids[expense.id] = expense.budget_line_id

        result = super().write(vals)

        # Update budget line actual_amount when expense is linked or amount changes
        if budget_line_changed or amount_changed:
            for expense in self:
                # If budget_line_id was set, update the budget line
                if expense.budget_line_id:
                    expense._update_budget_line_amount()

                # If budget_line_id was removed, clear the link on the old budget line
                old_budget_line = old_budget_line_ids.get(expense.id)
                if old_budget_line and old_budget_line != expense.budget_line_id:
                    if old_budget_line.expense_id == expense:
                        old_budget_line.sudo().with_context(
                            skip_expense_update=True
                        ).write({'expense_id': False})

        return result

    def _update_budget_line_amount(self):
        """Update the linked budget line's actual_amount from expense amount."""
        self.ensure_one()
        if not self.budget_line_id:
            return

        # Update actual_amount from expense total_amount_currency
        # Use context flag to prevent circular updates from budget_line.write()
        # Always update, even if amount is 0 (to clear the amount if expense is set to 0)
        budget_line = self.budget_line_id.sudo().with_context(skip_expense_update=True)
        budget_line.write({
            'actual_amount': self.total_amount_currency or 0.0,
            'expense_id': self.id,
            'date_actual': self.date
        })

        # Explicitly trigger parent budget recomputation
        if budget_line.budget_id:
            budget_line.budget_id._compute_actual_costs()