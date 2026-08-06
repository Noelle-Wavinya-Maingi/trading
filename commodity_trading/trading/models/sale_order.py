from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    trade_id = fields.Many2one('trading.trade', string="Related Trade")
    
    @api.onchange('trade_id')
    def _onchange_trade_id(self):
        """When trade is selected, you can show trade info"""
        if self.trade_id:
            _logger.info(f"✨ Linking sale order to trade: {self.trade_id.name}")

    def action_confirm(self):
        """Override confirm method to update trade when sales order is confirmed"""
        result = super().action_confirm()

        for order in self:
            if not order.trade_id:
                # Only lines whose product is flagged as a trade product feed the
                # trade — ordinary sales (services, supplies, non-traded goods)
                # should never spawn a trade.
                trade_lines = order.order_line.filtered(lambda l: l.product_id.is_tradeable)
                if not trade_lines:
                    _logger.info(f"No trade products on sale order {order.name}, skipping trade creation.")
                    continue

                # If no trade selected, try to create one
                _logger.info(f"📝 No trade selected for sale order {order.name}, checking if trade needs to be created...")
                total_qty = sum(trade_lines.mapped('product_uom_qty'))
                if total_qty > 0:
                    trade = self._create_trade_from_sale_order(order)
                    if trade:
                        order.write({'trade_id': trade.id})
                        _logger.info(f"✅ Created new trade {trade.name} for sale order {order.name}")
                continue
            
            # Update the trade with this sale order
            trade = order.trade_id
            _logger.info(f"🌼 Processing sale order {order.name} for trade {trade.name}")
            
            # Add this sale order to the trade's sale orders if not already linked
            if order not in trade.sale_order_ids:
                trade.write({'sale_order_ids': [(4, order.id)]})
            
            # Recompute all trade calculations
            trade._compute_all_trade_fields()
            
            # Check if trade should be closed based on quantity — scoped to
            # lines matching this trade's product, in case a linked SO also
            # carries non-trade or other-product lines
            confirmed_sos = trade.sale_order_ids.filtered(lambda so: so.state in ['sale', 'done'])
            total_sold_qty = sum(
                confirmed_sos.mapped('order_line').filtered(lambda l: l.product_id == trade.product_id).mapped('product_uom_qty')
            )
            if total_sold_qty >= trade.quantity:
                _logger.info(f"🏁 Trade {trade.name} fully sold ({total_sold_qty}/{trade.quantity}), closing...")
                trade.write({'status': 'closed'})
                trade._compute_all_trade_fields()
                
                # Post activity
                order.activity_schedule(
                    'mail.mail_activity_data_todo',
                    summary=_('Sales Order Confirmed - Trade Completed'),
                    note=_(
                        """
                        <p>The following sales order has been confirmed:</p>
                        <ul>
                            <li><strong>Trade:</strong> <a href=# data-oe-model=trading.trade data-oe-id=%(trade_id)s>%(trade_name)s</a></li>
                            <li><strong>Customer:</strong> %(partner_name)s</li>
                            <li><strong>Date:</strong> %(date)s</li>
                            <li><strong>Total:</strong> %(total)s</li>
                        </ul>
                        <p>Trade has been fully sold and closed.</p>
                        """,
                        trade_id=trade.id,
                        trade_name=trade.name,
                        partner_name=order.partner_id.name,
                        date=fields.Datetime.now(),
                        total=order.amount_total,
                    ),
                    user_id=order.user_id.id or self.env.user.id
                )
            else:
                _logger.info(f"⏳ Trade {trade.name} partially sold ({total_sold_qty}/{trade.quantity})")

        return result
    
    def _create_trade_from_sale_order(self, order):
        """Create a new trade from a sale order"""
        try:
            trade_lines = order.order_line.filtered(lambda l: l.product_id.is_tradeable)
            total_qty = sum(trade_lines.mapped('product_uom_qty'))
            total_value = sum(line.price_unit * line.product_uom_qty for line in trade_lines)
            avg_price = total_value / total_qty if total_qty > 0 else 0.0

            product = trade_lines[0].product_id if trade_lines else False
            
            # Determine trade type based on sale order type (default to long for sales)
            trade_type = 'short'
            
            trade_vals = {
                'trade_type': trade_type,
                'quantity': total_qty,
                'sales_price': avg_price,
                'sale_currency_id': order.currency_id.id,
                'status': 'confirmed',
                'product_id': product.id if product else False,
                'sale_order_ids': [(4, order.id)],
            }
            
            trade = self.env['trading.trade'].create(trade_vals)
            trade._compute_all_trade_fields()
            
            order.activity_schedule(
                'mail.mail_activity_data_todo',
                summary=_('Sales Order Confirmed - New Trade Created'),
                note=_(
                    """
                    <p>A new trade has been automatically created for this sale order:</p>
                    <ul>
                        <li><strong>Trade:</strong> %(trade_name)s</li>
                        <li><strong>Product:</strong> %(product_name)s</li>
                        <li><strong>Quantity:</strong> %(quantity)s</li>
                        <li><strong>Price:</strong> %(price)s %(currency_symbol)s</li>
                    </ul>
                    <p><strong>Note:</strong> This is a sales trade. If you need to link to a purchase trade, please update the trade field manually.</p>
                    """,
                    trade_name=trade.name,
                    product_name=product.name if product else _('N/A'),
                    quantity=trade.quantity,
                    price=trade.sales_price,
                    currency_symbol=trade.currency_id.symbol,
                ),
                user_id=order.user_id.id or self.env.user.id
            )
            
            return trade
            
        except Exception as e:
            order.message_post(body=_(
                """
                Error creating trade:
                %(error)s
                Please create the trade manually.
                """,
                error=str(e),
            ))
            return False