# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    omni_ops_file_ids = fields.Many2many('omni.ops.file', compute='_compute_omni_ops_file_ids')
    omni_ops_file_count = fields.Integer(compute='_compute_omni_ops_file_ids')

    @api.depends('order_line')
    def _compute_omni_ops_file_ids(self):
        for order in self:
            files = self.env['omni.ops.file'].search([('sale_line_id', 'in', order.order_line.ids)])
            order.omni_ops_file_ids = files
            order.omni_ops_file_count = len(files)

    def action_view_omni_ops_files(self):
        self.ensure_one()
        action = {
            'name': _('Freight Files'),
            'type': 'ir.actions.act_window',
            'res_model': 'omni.ops.file',
            'context': {'default_sale_line_id': self.order_line[:1].id},
        }
        if len(self.omni_ops_file_ids) == 1:
            action.update(view_mode='form', res_id=self.omni_ops_file_ids.id)
        else:
            action.update(view_mode='list,form', domain=[('id', 'in', self.omni_ops_file_ids.ids)])
        return action
