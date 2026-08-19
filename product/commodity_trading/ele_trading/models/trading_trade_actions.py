from odoo import models, fields, api


class TradingTradeActions(models.Model):
    """Stat-button counters and their smart-button navigation actions."""
    _inherit = 'trading.trade'

    ele_sale_count = fields.Integer(string="Sale Orders Count", compute="_compute_sale_count")

    ele_purchase_count = fields.Integer(string="Purchase Orders", compute="_compute_purchase_count")

    ele_invoice_count = fields.Integer(string='Invoice Count', compute='_compute_invoice_count')
    ele_bill_count = fields.Integer(string='Bill Count', compute='_compute_invoice_count')

    def _compute_purchase_count(self):
        """Compute the purchase orders attached to the trade"""
        for record in self:
            record.ele_purchase_count = 1 if record.ele_purchase_id else 0

    def _compute_sale_count(self):
        """Compute the sale orders attached to the trade"""
        for record in self:
            record.ele_sale_count = len(record.ele_sale_order_ids)

    @api.depends('invoice_ids', 'invoice_ids.move_type', 'invoice_ids.state')
    def _compute_invoice_count(self):
        """Compute all the invoices attached to the trade."""
        for record in self:
            # moves = self.env['account.move'].search([('ele_trade_id', '=', record.id)])
            invoices = record.invoice_ids.filtered(lambda m: m.move_type in ['out_invoice', 'out_refund'])
            bills = record.invoice_ids.filtered(lambda m: m.move_type in ['in_invoice', 'in_refund'])
            record.ele_invoice_count = len(invoices)
            record.ele_bill_count = len(bills)

    def action_view_purchase(self):
        """Method to view the attached purchase orders"""
        self.ensure_one()
        if not self.ele_purchase_id:
            return False
        return {
            'type': 'ir.actions.act_window',
            'name': 'Purchase Order',
            'res_model': 'purchase.order',
            'view_mode': 'form',
            'res_id': self.ele_purchase_id.id,
            'target': 'current',
        }

    def action_view_sales(self):
        """Method to view the attached sale orders"""
        self.ensure_one()
        if not self.ele_sale_order_ids:
            return False
        action = self.env.ref('sale.action_orders').read()[0]
        if len(self.ele_sale_order_ids) == 1:
            action['views'] = [(False, 'form')]
            action['res_id'] = self.ele_sale_order_ids.id
        else:
            action['domain'] = [('id', 'in', self.ele_sale_order_ids.ids)]
        return action

    def action_view_invoices(self):
        """Method to view the attached invoices"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Invoices',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('ele_trade_id', '=', self.id), ('move_type', 'in', ['out_invoice', 'out_refund'])],
            'context': {'default_ele_trade_id': self.id, 'default_move_type': 'out_invoice'},
        }

    def action_view_bills(self):
        """Method to view attached Bills"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Bills',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('ele_trade_id', '=', self.id), ('move_type', 'in', ['in_invoice', 'in_refund'])],
            'context': {'default_ele_trade_id': self.id, 'default_move_type': 'in_invoice'},
        }