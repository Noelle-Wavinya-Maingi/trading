# -*- coding: utf-8 -*-
from odoo import api, fields, models


class AccountMove(models.Model):
    """Freight shipment details shown on a vendor bill.

    These used to live in the same file as the bill approval workflow, which
    forced that workflow to depend on `quotation` (the ports, container type and
    container count are all related through freight fields on sale.order). The
    workflow now lives in omni_ap_validation with no freight dependency, and
    only these fields remain freight-specific."""
    _inherit = 'account.move'

    # Shipment details
    sale_order_ref = fields.Many2one('sale.order', compute="_compute_sale_order_ref", store=True)
    port_of_loading = fields.Many2one('port', string="Port of Loading", related="sale_order_ref.port_of_loading", store=True)
    port_of_dispatch = fields.Many2one('port', string="Port of Discharge", related="sale_order_ref.port_of_dispatch", store=True)
    container_size = fields.Selection(
        string="Container Size", related="sale_order_ref.container_type", store=True)
    no_of_containers = fields.Integer(string="No. of Containers", related="sale_order_ref.no_of_containers", store=True)
    marks = fields.Char(string="Marks/Numbers")
    goods_description = fields.Text(string="Goods Description")
    loading_date = fields.Date(string="Loading/Service Date")
    vessel = fields.Char(string="Vessel Name")
    file_number = fields.Char(string="File Number")

    @api.depends('invoice_origin')
    def _compute_sale_order_ref(self):
        for invoice in self:
            sale_order = False
            if invoice.invoice_origin:
                sale_order = self.env['sale.order'].search([
                    ('name', '=', invoice.invoice_origin)
                ], limit=1)

            invoice.sale_order_ref = sale_order.id if sale_order else False
