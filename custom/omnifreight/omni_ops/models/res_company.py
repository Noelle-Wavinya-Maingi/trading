# -*- coding: utf-8 -*-
from odoo import fields, models

# Fallback defaults, used only when a company has not configured its own values.
# These reproduce the literals that were previously hardcoded throughout this
# module, so an existing install behaves identically until it is configured.
DEFAULT_SERVICE_CATEGORY_NAME = 'Omnifreight Services'


class ResCompany(models.Model):
    """Per-company configuration for freight operations.

    Everything here was previously a literal buried in this module's Python --
    a product category matched by name, a pair of Belgian GL account codes, a
    set of English keyword patterns, workcenters resolved by fuzzy name match,
    and a hardcoded approver group. None of those hold for a second freight
    client, so each is now configurable, with the original literal kept as the
    fallback default so existing installs are unaffected."""
    _inherit = 'res.company'

    omni_service_category_id = fields.Many2one(
        'product.category',
        string='Freight Service Product Category',
        help="Category assigned to freight service products. If unset, falls back "
             "to a category named '%s'." % DEFAULT_SERVICE_CATEGORY_NAME,
    )
    omni_fob_workcenter_id = fields.Many2one(
        'mrp.workcenter', string='FOB Workcenter',
        help="Workcenter used for FOB service operations.",
    )
    omni_freight_workcenter_id = fields.Many2one(
        'mrp.workcenter', string='Freight Workcenter',
        help="Workcenter used for Freight service operations.",
    )
    omni_lod_workcenter_id = fields.Many2one(
        'mrp.workcenter', string='Destination (LOD) Workcenter',
        help="Workcenter used for Destination/LOD service operations.",
    )
    # === RESOLVERS (configured value first, historical literal as fallback) ===
    def _omni_get_service_category(self):
        """Product category for freight service products."""
        self.ensure_one()
        if self.omni_service_category_id:
            return self.omni_service_category_id
        return self.env['product.category'].search(
            [('name', '=', DEFAULT_SERVICE_CATEGORY_NAME)], limit=1
        )

    def _omni_get_workcenter(self, service_type):
        """Resolve the workcenter backing a service type.

        Prefers the explicitly configured workcenter. Falls back to the previous
        behaviour -- a fuzzy name match, then creating one -- so nothing breaks on
        an unconfigured install. Note the fallback's `ilike` is deliberately
        imprecise and can match an unrelated workcenter; configuring the fields
        above is what makes this deterministic."""
        self.ensure_one()
        if not service_type:
            return self.env['mrp.workcenter']

        configured = {
            'fob': self.omni_fob_workcenter_id,
            'freight': self.omni_freight_workcenter_id,
            'lod': self.omni_lod_workcenter_id,
        }.get(service_type)
        if configured:
            return configured

        Workcenter = self.env['mrp.workcenter']
        workcenter = Workcenter.search([('name', 'ilike', service_type)], limit=1)
        if not workcenter:
            workcenter = Workcenter.create({
                'name': f'{service_type.upper()} Operations',
                'code': service_type.upper(),
            })
        return workcenter
