from odoo import models, fields, api


class TradingFutureDeliveryLine(models.Model):
    _name = 'trading.future.delivery.line'
    _description = 'Future Delivery Line'
    _order = 'delivery_date desc'

    future_id = fields.Many2one('trading.futures', string='Future', required=True, ondelete='cascade')
    picking_id = fields.Many2one('stock.picking', string='Delivery Order', required=True)
    lot_id = fields.Many2one('stock.lot', string='Lot/Serial Number')
    quantity = fields.Float(string='Quantity', required=True, digits=(16, 2))
    sale_price = fields.Float(string='Sale Price', digits=(16, 2), required=True)
    delivery_date = fields.Datetime(string='Delivery Date', default=fields.Datetime.now)

    # Computed fields for this delivery line
    contract_value = fields.Float(
        string='Contract Value',
        compute='_compute_values',
        digits=(16, 2),
        store=True
    )

    sales_value = fields.Float(
        string='Sales Value',
        compute='_compute_values',
        digits=(16, 2),
        store=True
    )

    realized_pnl = fields.Float(
        string='Realized P&L',
        compute='_compute_values',
        digits=(16, 2),
        store=True,
        help='Profit/Loss on this delivery'
    )

    # Related fields for context
    sale_order_id = fields.Many2one('sale.order', string='Sale Order', related='picking_id.sale_id', store=True)
    partner_id = fields.Many2one('res.partner', string='Customer', related='picking_id.partner_id', store=True)

    @api.depends('quantity', 'sale_price', 'future_id.contract_price')
    def _compute_values(self):
        for line in self:
            contract_price = line.future_id.contract_price or 0
            line.contract_value = line.quantity * contract_price
            line.sales_value = line.quantity * (line.sale_price or 0)
            line.realized_pnl = line.sales_value - line.contract_value

    def write(self, vals):
        """Override write to trigger future recomputation"""
        result = super().write(vals)

        # Trigger recomputation on related futures
        if any(field in vals for field in ['quantity', 'sale_price']):
            self.mapped('future_id')._compute_sales_values()
            self.mapped('future_id')._compute_net_value()
            self.mapped('future_id')._compute_pnl_details()
            self.mapped('future_id')._compute_pnl()

        return result

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)

        # Trigger recomputation on related futures
        for record in records:
            if record.future_id:
                record.future_id._compute_sales_values()
                record.future_id._compute_net_value()
                record.future_id._compute_pnl_details()
                record.future_id._compute_pnl()

        return records
