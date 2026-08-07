# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class MrpProduction(models.Model):
    """Budget-side extension of a freight manufacturing order.

    These fields and actions used to live in omni_ops' own mrp.production
    extension, which meant core freight operations could not be installed
    without the whole budgeting feature. Moving them here inverts the
    dependency: omni_ops knows nothing about budgets, and this module adds
    them on top -- the same shape trading_budget uses to bolt budgets onto
    trading."""
    # _name is required alongside a LIST _inherit when extending an existing
    # model with an additional mixin -- see omni_mrp_workorder.py for the
    # same pattern.
    _name = 'mrp.production'
    _inherit = ['mrp.production', 'budget.bridge.mixin']

    # === BUDGET FIELDS ===
    # has_budget comes from budget.bridge.mixin; this model just supplies
    # the budget_ids One2many the mixin's compute depends on.
    budget_ids = fields.One2many(
        'omni.mrp.budget',
        'production_id',
        string='Budgets'
    )
    budget_id = fields.Many2one(
        'omni.mrp.budget',
        string='Active Budget',
        compute='_compute_active_budget',
        store=True
    )
    budget_state = fields.Selection(
        related='budget_id.state',
        string='Budget Status',
        readonly=True
    )

    # === BUDGET METHODS ===
    @api.depends('budget_ids')
    def _compute_active_budget(self):
        """Set the active budget (most recent non-closed budget)."""
        for production in self:
            if production.budget_ids:
                # Get most recent budget (by create_date desc)
                active_budget = production.budget_ids.sorted('create_date', reverse=True)[0]
                production.budget_id = active_budget.id
            else:
                production.budget_id = False

    def action_create_budget(self):
        """Create a budget for this manufacturing order."""
        self.ensure_one()

        if self.budget_ids:
            raise ValidationError(_("This manufacturing order already has a budget."))

        # Get currency from sale order or use company currency
        currency_id = self.env.company.currency_id
        if self.sale_line_id and self.sale_line_id.order_id:
            currency_id = self.sale_line_id.order_id.currency_id

        budget = self.env['omni.mrp.budget'].create({
            'production_id': self.id,
            'currency_id': currency_id.id,
        })

        # Automatically copy charges from quotation
        if self.sale_line_id and self.sale_line_id.order_id:
            budget.action_copy_charges_from_quotation()

        return {
            'type': 'ir.actions.act_window',
            'name': _('Budget'),
            'res_model': 'omni.mrp.budget',
            'res_id': budget.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_view_budget(self):
        """View the budget for this manufacturing order."""
        self.ensure_one()

        if not self.budget_id:
            raise ValidationError(_("No budget found for this manufacturing order."))

        return {
            'type': 'ir.actions.act_window',
            'name': _('Budget'),
            'res_model': 'omni.mrp.budget',
            'res_id': self.budget_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_open_budgets(self):
        """Open all budgets for this manufacturing order."""
        self.ensure_one()

        return {
            'type': 'ir.actions.act_window',
            'name': _('Budgets'),
            'res_model': 'omni.mrp.budget',
            'domain': [('production_id', '=', self.id)],
            # 'tree' was renamed to 'list' in Odoo 17 and raises on 19.
            'view_mode': 'list,form',
            'target': 'current',
        }
