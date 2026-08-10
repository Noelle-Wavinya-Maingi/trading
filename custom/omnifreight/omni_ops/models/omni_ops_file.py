# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class OmniOpsFile(models.Model):
    """Freight file, the anchor for a set of operational steps (omni.ops.step) that
    are generated from a freight service step template (omni.service.step.template)."""
    _name = 'omni.ops.file'
    _description = 'Freight File'
    _inherit = ['process.bridge.mixin']
    _order = 'id desc'

    name = fields.Char(compute='_compute_name', store=True)
    origin = fields.Char(string='Source Document')
    # The product and quantity being shipped. These are used to generate the operational steps, and also to link the freight file to a sale order line if applicable.
    product_id = fields.Many2one('product.product', string='Product', required=True)
    product_qty = fields.Float(string='Quantity', default=1.0)
    product_uom_id = fields.Many2one('uom.uom', string='Unit of Measure')
    # The sale order line that this freight file is linked to, if any. This is used to link the freight file to the sale order and to generate the operational steps.
    sale_line_id = fields.Many2one('sale.order.line', string='Sale Order Line', index=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    step_ids = fields.One2many('omni.ops.step', 'file_id', string='Steps')

    has_fob_service = fields.Boolean(string='Has FOB Service', compute='_compute_service_flags', store=True)
    has_freight_service = fields.Boolean(string='Has Freight Service', compute='_compute_service_flags', store=True)
    has_lod_service = fields.Boolean(string='Has LOD Service', compute='_compute_service_flags', store=True)

    @api.depends('origin')
    def _compute_name(self):
        """Set the name of the freight file to the origin document if present, otherwise 'New'."""
        for file in self:
            file.name = file.origin or _('New')

    @api.depends('step_ids.service_type')
    def _compute_service_flags(self):
        """Set the service flags based on the service types of the operational steps."""
        for file in self:
            service_types = set(file.step_ids.mapped('service_type'))
            file.has_fob_service = 'fob' in service_types
            file.has_freight_service = 'freight' in service_types
            file.has_lod_service = 'lod' in service_types
