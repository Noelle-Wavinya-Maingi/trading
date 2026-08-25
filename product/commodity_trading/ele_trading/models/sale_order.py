import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    # _name is required alongside a LIST _inherit when extending an existing
    # model with an additional mixin -- see omni_mrp_workorder.py for the
    # same pattern.
    _name = 'sale.order'
    _inherit = ['sale.order', 'order.bridge.mixin']

    ele_trade_id = fields.Many2one('trading.trade', string="Related Trade")

    @api.onchange('ele_trade_id')
    def _onchange_trade_id(self):
        """When trade is selected, you can show trade info"""
        if self.ele_trade_id:
            _logger.info(f"Linking sale order to trade: {self.ele_trade_id.name}")

    def action_confirm(self):
        """Override confirm method to update trade when sales order is confirmed"""
        result = super().action_confirm()

        for order in self:
            # Log the order being processed and its state after confirmation
            for group, trade, was_created in order._bridge_run_definition(order._trading_sale_bridge_definition()):
                if was_created:
                    _logger.info(f"Created new trade {trade.name} for sale order {order.name}")
                else:
                    # Update path: this trade was already linked before confirm.
                    _logger.info(f"Processing sale order {order.name} for trade {trade.name}")
                    trade._compute_all_trade_fields()

                was_confirmed = trade.ele_status == 'confirmed'
                trade._auto_close_if_fully_matched()

                if was_confirmed and trade.ele_status == 'closed':
                    _logger.info(f"Trade {trade.name} fully matched, closed")

                    order.activity_schedule(
                        'mail.mail_activity_data_todo',
                        summary=_('Sales Order Confirmed - Trade Completed'),
                        note=_(
                            """
                            <p>The following sales order has been confirmed:</p>
                            <ul>
                                <li><strong>Trade:</strong> <a href=# data-oe-model=trading.trade data-oe-id=%(ele_trade_id)s>%(trade_name)s</a></li>
                                <li><strong>Customer:</strong> %(partner_name)s</li>
                                <li><strong>Date:</strong> %(date)s</li>
                                <li><strong>Total:</strong> %(total)s</li>
                            </ul>
                            <p>Trade has been fully sold and closed.</p>
                            """,
                            ele_trade_id=trade.id,
                            trade_name=trade.name,
                            partner_name=order.partner_id.name,
                            date=fields.Datetime.now(),
                            total=order.amount_total,
                        ),
                        user_id=order.user_id.id or self.env.user.id
                    )
                else:
                    _logger.info(f"⏳ Trade {trade.name} not yet fully matched (status={trade.ele_status})")

        return result

    # === order.bridge.mixin registration ===
    # Trading aggregates every tradeable line on the order into a single
    # trade (one group, not one per line -- see omnifreight_quotation.py for
    # the opposite grouping), and this is the "short" (sold-first) side.
    #
    # Unlike purchase_order.py, only the CREATE path is gated on having
    # tradeable lines -- once a trade is already linked, the update path
    # runs regardless of current order_line contents (it may need closing
    def _bridge_definitions(self):
        return super()._bridge_definitions() + [self._trading_sale_bridge_definition()]

    def _trading_sale_bridge_definition(self):
        return {
            'qualifying_lines': self._trading_sale_bridge_qualifying_lines,
            'group_lines': self._trading_sale_bridge_group_lines,
            'find_existing': self._trading_sale_bridge_find_existing,
            'vals': self._trading_sale_bridge_vals,
            'record_model': self._trading_sale_bridge_record_model,
            'create': self._trading_sale_bridge_create,
            'link': self._trading_sale_bridge_link,
        }

    def _trading_sale_bridge_qualifying_lines(self):
        self.ensure_one()
        if self.ele_trade_id:
            return self

        # Only lines whose product is flagged as a trade product feed the
        # trade — ordinary sales (services, supplies, non-traded goods)
        # should never spawn a trade.
        trade_lines = self.order_line.filtered(lambda l: l.product_id.ele_is_tradeable)
        if not trade_lines:
            _logger.info(f"No trade products on sale order {self.name}, skipping trade creation.")
            return trade_lines

        total_qty = sum(trade_lines.mapped('product_uom_qty'))
        if total_qty <= 0:
            return self.env['sale.order.line']

        return trade_lines

    def _trading_sale_bridge_group_lines(self, lines):
        return [lines]

    def _trading_sale_bridge_record_model(self):
        return 'trading.trade'

    def _trading_sale_bridge_find_existing(self, group):
        return self.ele_trade_id

    def _trading_sale_bridge_vals(self, group, existing):
        if existing:
            # Only field this path ever touches: add this order to the
            # trade's ele_sale_order_ids if it isn't already there.
            if self not in existing.ele_sale_order_ids:
                return {'ele_sale_order_ids': [(4, self.id)]}
            return {}

        trade_lines = group
        order = self

        total_qty = sum(trade_lines.mapped('product_uom_qty'))
        total_value = sum(line.price_unit * line.product_uom_qty for line in trade_lines)
        avg_price = total_value / total_qty if total_qty > 0 else 0.0

        product = trade_lines[0].product_id if trade_lines else False

        return {
            'ele_trade_type': 'short',
            'quantity': total_qty,
            'ele_sales_price': avg_price,
            'ele_sale_currency_id': order.currency_id.id,
            'ele_status': 'confirmed',
            'product_id': product.id if product else False,
            'ele_sale_order_ids': [(4, order.id)],
        }

    def _trading_sale_bridge_create(self, vals):
        """Swallow-and-notify on creation failure rather than aborting the
        whole action_confirm batch -- matches the original behavior, which
        only wrapped the create path (not the update path) this way, and
        posted the error to the order's own chatter rather than just
        logging it."""
        order = self
        try:
            trade = self._bridge_default_create('trading.trade', vals)
            trade._compute_all_trade_fields()

            product_id = vals.get('product_id')
            product = self.env['product.product'].browse(product_id) if product_id else False

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
                    price=trade.ele_sales_price,
                    currency_symbol=trade.currency_id.symbol,
                ),
                user_id=order.user_id.id or self.env.user.id
            )

            return trade

        except (ValueError, KeyError, AttributeError, UserError, ValidationError) as e:
            order.message_post(body=_(
                """
                Error creating trade:
                %(error)s
                Please create the trade manually.
                """,
                error=str(e),
            ))
            return self.env['trading.trade']

    def _trading_sale_bridge_link(self, group, record):
        self.ele_trade_id = record.id
