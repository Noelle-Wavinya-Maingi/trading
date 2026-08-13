# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class BudgetBridgeMixin(models.AbstractModel):
    """Mixin for models that can have a budget."""
    _name = 'budget.bridge.mixin'
    _description = 'Budget Bridge Mixin'

    has_budget = fields.Boolean('Has Budget', compute='_compute_has_budget', store=True)
    budget_state = fields.Selection(
        [('draft', 'Draft'), ('confirmed', 'Confirmed'), ('closed', 'Closed')],
        string='Budget Status',
        compute='_compute_budget_state',
    )

    @api.depends('budget_ids')
    def _compute_has_budget(self):
        """Compute whether the record has any associated budgets."""
        for record in self:
            record.has_budget = bool(record.budget_ids)

    @api.depends('budget_id.state')
    def _compute_budget_state(self):
        """Compute the state of the associated budget, if any."""
        for record in self:
            record.budget_state = record.budget_id.state if record.budget_id else False

    def _bridge_open_budget_action(self, budget):
        """Return an action to open the given budget in a form view. Raises a ValidationError if no budget is provided."""
        self.ensure_one()
        if not budget:
            raise ValidationError(_("No budget found for %s.") % self.display_name)

        return {
            'type': 'ir.actions.act_window',
            'name': _('Budget'),
            'res_model': budget._name,
            'res_id': budget.id,
            'view_mode': 'form',
            'target': 'current',
        }
