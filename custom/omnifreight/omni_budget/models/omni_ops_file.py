# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class OmniOpsFile(models.Model):
    """Freight file for a shipment. Each file has a service scope (FOB, Freight, Destination) and is linked to a quotation,
    and can have multiple budgets (omni.mrp.budget) associated with it. The active budget is the most recent non-closed budget."""
    _name = 'omni.ops.file'
    _inherit = ['omni.ops.file', 'budget.bridge.mixin']

    # === BUDGET FIELDS ===
    budget_ids = fields.One2many(
        'omni.mrp.budget',
        'file_id',
        string='Budgets'
    )
    budget_id = fields.Many2one(
        'omni.mrp.budget',
        string='Active Budget',
        compute='_compute_active_budget',
        store=True
    )

    # === BUDGET METHODS ===
    @api.depends('budget_ids')
    def _compute_active_budget(self):
        """Set the active budget (most recent non-closed budget)."""
        for file in self:
            if file.budget_ids:
                active_budget = file.budget_ids.sorted('create_date', reverse=True)[0]
                file.budget_id = active_budget.id
            else:
                file.budget_id = False

    def action_create_budget(self):
        """Create a budget for this freight file."""
        self.ensure_one()

        if self.budget_ids:
            raise ValidationError(_("This freight file already has a budget."))

        currency_id = self.env.company.currency_id
        if self.sale_line_id and self.sale_line_id.order_id:
            currency_id = self.sale_line_id.order_id.currency_id

        budget = self.env['omni.mrp.budget'].create({
            'file_id': self.id,
            'currency_id': currency_id.id,
        })

        if self.sale_line_id and self.sale_line_id.order_id:
            budget.action_copy_charges_from_quotation()

        return self._bridge_open_budget_action(budget)

    def action_view_budget(self):
        """View the budget for this freight file."""
        return self._bridge_open_budget_action(self.budget_id)

    def action_open_budgets(self):
        """Open all budgets for this freight file."""
        self.ensure_one()

        return {
            'type': 'ir.actions.act_window',
            'name': _('Budgets'),
            'res_model': 'omni.mrp.budget',
            'domain': [('file_id', '=', self.id)],
            'view_mode': 'list,form',
            'target': 'current',
        }
