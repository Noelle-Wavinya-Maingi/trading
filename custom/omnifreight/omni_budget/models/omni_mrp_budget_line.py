# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class OmniMrpBudgetLine(models.Model):
    """Budget line for a freight budget. Each line is linked to a budget (omni.mrp.budget) and has a service type (FOB, Freight, LOD).
    The service type is used to group lines in the budget view and to determine which opening steps to create for the budget."""
    _inherit = 'operations.budget.line'
    _order = 'service_type, sequence, id'

    mrp_budget_id = fields.Many2one(
        'omni.mrp.budget',
        # Distinct from trading_budget's ele_trade_budget_id label: two fields on the
        # same model sharing a label makes Odoo warn and the UI ambiguous.
        #
        # Not required: operations.budget.line is a shared table -- when
        # ele_trading_budget is also installed, a trading-only line has no
        # freight budget at all, and a NOT NULL constraint here would break
        # every trading budget line the moment both verticals coexist in
        # one database (this broke exactly that way; see the base model's
        # `_get_anchor_record` docstring, which already tolerates "no
        # anchor" as a normal case).
        string='Freight Budget',
        ondelete='cascade',
        index=True
    )

    # === SERVICE TYPE ===
    service_type = fields.Selection([
        ('fob', 'FOB'),
        ('freight', 'Freight'),
        ('lod', 'LOD (Destination)')
    ], string='Service Type', required=True, index=True, default='fob')

    @api.model
    def default_get(self, fields_list):
        """Set default service_type based on context."""
        res = super().default_get(fields_list)

        if 'default_service_type' in self.env.context:
            service_type = self.env.context.get('default_service_type')
            if service_type in ('fob', 'freight', 'lod'):
                res['service_type'] = service_type
        elif 'default_fob_operation' in self.env.context:
            res['service_type'] = 'fob'
        elif 'default_freight_operation' in self.env.context:
            res['service_type'] = 'freight'
        elif 'default_lod_operation' in self.env.context:
            res['service_type'] = 'lod'

        return res

    @api.constrains('service_type')
    def _check_service_type(self):
        """Ensure service_type is valid and preserved."""
        for line in self:
            if line.service_type not in ('fob', 'freight', 'lod'):
                raise ValidationError(_("Invalid service type '%s' for budget line '%s'.") % (line.service_type, line.name))

    # === ANCHOR PROVIDER REGISTRATION ===
    # Registered via _anchor_providers() rather than overriding
    # _get_anchor_record()/etc. directly, since ele_trading_budget also
    # extends operations.budget.line with its own anchor -- see
    # operations_budget_line.py's (shared/budgets) docstring for why bare
    # hook-method overrides would collide between the two.

    def _anchor_providers(self):
        return super()._anchor_providers() + [{
            'owns_line': lambda: bool(self.mrp_budget_id),
            'anchor_record': self._freight_anchor_record,
            'anchor_link_vals': self._freight_anchor_link_vals,
            'display_name_prefix': self._freight_anchor_display_name_prefix,
            'notify_amount_change': self._freight_anchor_notify_amount_change,
            'conversion_company': self._freight_anchor_conversion_company,
            'target_currency': self._freight_anchor_target_currency,
        }]

    def _freight_anchor_record(self):
        """Return the anchor record for this budget line, which is the omni.mrp.budget record it belongs to."""
        return self.mrp_budget_id

    def _freight_anchor_link_vals(self):
        """Return the values to link this budget line's actualizing expense
        to the same freight file as its budget."""
        file = self.mrp_budget_id.file_id if self.mrp_budget_id else False
        if not file:
            return {}
        return {'file_id': file.id}

    def _freight_anchor_display_name_prefix(self):
        """Return a prefix for the display name of this budget line, based on its anchor record."""
        anchor = self.mrp_budget_id
        if not anchor or not anchor.file_id:
            return ''
        return anchor.file_id.name

    def _freight_anchor_notify_amount_change(self):
        """Notify the anchor record that the amount of this budget line has changed, so it can update its totals."""
        if self.mrp_budget_id:
            self.mrp_budget_id._compute_actual_costs()
            self.mrp_budget_id._compute_margin_display()

    def _freight_anchor_conversion_company(self):
        """Return the company to use for currency conversion. If the budget line is linked to a budget, use the budget's company,
        otherwise use the current company."""
        if self.mrp_budget_id and self.mrp_budget_id.company_id:
            return self.mrp_budget_id.company_id
        return self.env.company

    def _freight_anchor_target_currency(self):
        """Return the target currency for this budget line, which is the currency of the budget's company."""
        return self._freight_anchor_conversion_company().currency_id
