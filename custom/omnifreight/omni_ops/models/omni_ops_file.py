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

    @api.depends('origin')
    def _compute_name(self):
        """Set the name of the freight file to the origin document if present, otherwise 'New'."""
        for file in self:
            file.name = file.origin or _('New')
