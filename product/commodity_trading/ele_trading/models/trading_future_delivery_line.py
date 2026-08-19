from odoo import models, fields, api


class TradingFutureDeliveryLine(models.Model):
    _name = 'trading.future.delivery.line'
    _description = 'Future Delivery Line'
    _order = 'ele_delivery_date desc'

    ele_future_id = fields.Many2one('trading.futures', string='Future', required=True, ondelete='cascade')
    ele_picking_id = fields.Many2one('stock.picking', string='Delivery Order', required=True)
    ele_lot_id = fields.Many2one('stock.lot', string='Lot/Serial Number')
    quantity = fields.Float(string='Quantity', required=True, digits=(16, 2))
    ele_sale_price = fields.Float(string='Sale Price', digits=(16, 2), required=True)
    ele_delivery_date = fields.Datetime(string='Delivery Date', default=fields.Datetime.now)

    # Computed fields for this delivery line
    ele_contract_value = fields.Float(
        string='Contract Value',
        compute='_compute_values',
        digits=(16, 2),
        store=True
    )

    ele_sales_value = fields.Float(
        string='Sales Value',
        compute='_compute_values',
        digits=(16, 2),
        store=True
    )

    ele_realized_pnl = fields.Float(
        string='Realized P&L',
        compute='_compute_values',
        digits=(16, 2),
        store=True,
        help='Profit/Loss on this delivery'
    )

    # Related fields for context
    ele_sale_order_id = fields.Many2one('sale.order', string='Sale Order', related='ele_picking_id.sale_id', store=True)
    partner_id = fields.Many2one('res.partner', string='Customer', related='ele_picking_id.partner_id', store=True)

    @api.depends('quantity', 'ele_sale_price', 'ele_future_id.ele_contract_price')
    def _compute_values(self):
        for line in self:
            ele_contract_price = line.ele_future_id.ele_contract_price or 0
            line.ele_contract_value = line.quantity * ele_contract_price
            line.ele_sales_value = line.quantity * (line.ele_sale_price or 0)
            line.ele_realized_pnl = line.ele_sales_value - line.ele_contract_value

    def write(self, vals):
        """Override write to trigger future recomputation"""
        result = super().write(vals)

        # Trigger recomputation on related futures
        if any(field in vals for field in ['quantity', 'ele_sale_price']):
            self.mapped('ele_future_id')._compute_sales_values()
            self.mapped('ele_future_id')._compute_net_value()
            self.mapped('ele_future_id')._compute_pnl_details()
            self.mapped('ele_future_id')._compute_pnl()

        return result

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)

        # Trigger recomputation on related futures
        for record in records:
            if record.ele_future_id:
                record.ele_future_id._compute_sales_values()
                record.ele_future_id._compute_net_value()
                record.ele_future_id._compute_pnl_details()
                record.ele_future_id._compute_pnl()

        return records
