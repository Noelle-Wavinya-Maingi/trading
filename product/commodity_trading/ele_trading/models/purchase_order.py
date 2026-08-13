import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)

class PurchaseOrder(models.Model):
    # _name is required alongside a LIST _inherit when extending an existing
    # model with an additional mixin -- see omni_mrp_workorder.py for the
    # same pattern.
    _name = 'purchase.order'
    _inherit = ['purchase.order', 'order.bridge.mixin']

    trade_id = fields.Many2one('trading.trade', string='Related Trade', ondelete='set null')

    # Add a smart button to view the trade
    trade_count = fields.Integer(
        string="Trade Count",
        compute="_compute_trade_count"
    )

    def _compute_trade_count(self):
        for order in self:
            order.trade_count = 1 if order.trade_id else 0

    def button_confirm(self):
        _logger.warning("🔘🔘🔘 button_confirm STARTED for %s 🔘🔘🔘", self.name)

        for order in self:
            _logger.warning("Before super - Order: %s, State: %s, Trade: %s",
                          order.name, order.state, order.trade_id.name if order.trade_id else None)

        result = super().button_confirm()

        _logger.warning("🔘🔘🔘 AFTER super() call - Processing trades 🔘🔘🔘")

        for order in self:
            _logger.warning("Processing order: %s", order.name)
            _logger.warning("Order state after confirmation: %s", order.state)

            # Run the trading bridge definition for this order and process the results
            for group, trade, was_created in order._bridge_run_definition(order._trading_purchase_bridge_definition()):
                trade._compute_all_trade_fields()

                if was_created:
                    _logger.warning('✅✅✅ SUCCESS: Created trade %s (ID: %s) from purchase %s ✅✅✅',
                                  trade.name, trade.id, order.name)
                    product = group[0].product_id if group else False
                    order.activity_schedule(
                        'mail.mail_activity_data_todo',
                        summary=_('Purchase Order Confirmed - New Trade Created'),
                        note=_(
                            """
                            <p>A new trade has been automatically created for this purchase order:</p>
                            <ul>
                                <li><strong>Trade:</strong> %(trade_name)s</li>
                                <li><strong>Product:</strong> %(product_name)s</li>
                                <li><strong>Quantity:</strong> %(quantity)s</li>
                                <li><strong>Price:</strong> %(price)s %(currency_symbol)s</li>
                            </ul>
                            <p><strong>Note:</strong> This is a purchase trade. If you need to link to a sales trade, please update the trade field manually.</p>
                            """,
                            trade_name=trade.name,
                            product_name=product.name if product else _('N/A'),
                            quantity=trade.quantity,
                            price=trade.price,
                            currency_symbol=trade.purchase_currency_id.symbol,
                        ),
                        user_id=order.user_id.id or self.env.user.id
                    )
                else:
                    _logger.warning(f"✅ Updated trade {trade.name}")
                    order.activity_schedule(
                        'mail.mail_activity_data_todo',
                        summary=_('Purchase Order Confirmed - Trade Complete'),
                        note=_(
                            """
                            <p>The following purchase order has been confirmed:</p>
                            <ul>
                                <li><strong>Trade:</strong> <a href=# data-oe-model=trading.trade data-oe-id=%(trade_id)s>%(trade_name)s</a></li>
                                <li><strong>Vendor:</strong> %(partner_name)s</li>
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

        # Outside the for loop — runs once per button click, not once per order,
        # and doesn't cut the loop short for a multi-order confirm.
        _logger.warning("🔘🔘🔘 button_confirm FINISHED for %s 🔘🔘🔘", self.name)
        return result

    # === order.bridge.mixin registration ===
    # Trading aggregates every tradeable line on the order into a single
    # trade (one group, not one per line -- see omnifreight_quotation.py for
    # the opposite grouping), and this is the "long" (bought-first) side.
    def _bridge_definitions(self):
        return super()._bridge_definitions() + [self._trading_purchase_bridge_definition()]

    def _trading_purchase_bridge_definition(self):
        return {
            'qualifying_lines': self._trading_purchase_bridge_qualifying_lines,
            'group_lines': self._trading_purchase_bridge_group_lines,
            'find_existing': self._trading_purchase_bridge_find_existing,
            'vals': self._trading_purchase_bridge_vals,
            'record_model': self._trading_purchase_bridge_record_model,
            'create': self._trading_purchase_bridge_create,
            'link': self._trading_purchase_bridge_link,
        }

    def _trading_purchase_bridge_qualifying_lines(self):
        self.ensure_one()
        trade_lines = self.order_line.filtered(lambda l: l.product_id.is_tradeable)
        if not trade_lines:
            return trade_lines

        trade_products = trade_lines.mapped('product_id')
        if len(trade_products) > 1:
            _logger.warning(
                'Purchase order %s has multiple distinct trade products (%s) — '
                'only %s will be used for this trade. Split trade products across '
                'separate orders if they need independent trades.',
                self.name, trade_products.mapped('name'), trade_products[0].name
            )

        # A trade that already exists must still be processed (its
        # currency/date/etc. may need syncing) regardless of quantity; a
        # trade that doesn't exist yet is only worth creating if there's
        # something to create it with.
        if not self.trade_id and sum(trade_lines.mapped('product_qty')) <= 0:
            _logger.warning('Purchase order %s has no quantity, skipping trade creation.', self.name)
            return self.env['purchase.order.line']

        return trade_lines

    def _trading_purchase_bridge_group_lines(self, lines):
        return [lines]

    def _trading_purchase_bridge_record_model(self):
        return 'trading.trade'

    def _trading_purchase_bridge_find_existing(self, group):
        return self.trade_id

    def _trading_purchase_bridge_vals(self, group, existing):
        trade_lines = group
        order = self

        total_qty = sum(trade_lines.mapped('product_qty'))
        total_value = sum(line.product_qty * line.price_unit for line in trade_lines)
        avg_price = total_value / total_qty if total_qty else 0.0

        _logger.warning("Total Quantity: %s, Total Value: %s, Avg Price: %s", total_qty, total_value, avg_price)

        if existing:
            trade = existing
            _logger.warning('Purchase order %s already has a trade (%s), updating trade with purchase order...',
                          order.name, trade.name)

            update_vals = {}
            if not trade.purchase_id:
                update_vals['purchase_id'] = order.id
                _logger.warning(f"Setting purchase_id on trade {trade.name} to {order.name}")

            # These two must be updated together with price — price is stored
            # in whatever currency purchase_currency_id says it's in. Updating
            # price without also syncing the currency (as this branch used to)
            # silently mislabels a foreign-currency amount as being in whatever
            # currency the trade happened to default to before a purchase existed.
            if trade.purchase_currency_id != order.currency_id:
                _logger.warning(
                    f"Currency mismatch: Trade has {trade.purchase_currency_id.name}, "
                    f"PO is in {order.currency_id.name}. Updating trade purchase currency."
                )
                update_vals['purchase_currency_id'] = order.currency_id.id

            po_date = order.date_order.date() if order.date_order else fields.Date.context_today(self)
            if trade.purchase_date != po_date:
                update_vals['purchase_date'] = po_date

            if trade.quantity != total_qty:
                _logger.warning(f"Quantity mismatch: Trade has {trade.quantity}, PO has {total_qty}. Updating trade quantity.")
                update_vals['quantity'] = total_qty

            if trade.price != avg_price:
                _logger.warning(f"Price mismatch: Trade has {trade.price}, PO has {avg_price}. Updating trade price.")
                update_vals['price'] = avg_price

            if not trade.product_id and trade_lines:
                product = trade_lines[0].product_id
                update_vals['product_id'] = product.id
                _logger.warning(f"Setting product on trade {trade.name} to {product.name}")

            if update_vals:
                _logger.warning(f"✅ Updating trade {trade.name} with: {update_vals}")
            else:
                _logger.warning(f"✅ Trade {trade.name} already has correct values")
            return update_vals

        lot = False
        if order.picking_ids:
            _logger.warning("Picking IDs found: %s", order.picking_ids.ids)
            move_lines = order.picking_ids.mapped('move_line_ids').filtered(
                lambda ml: ml.product_id == trade_lines[0].product_id
            )
            if move_lines:
                lot = move_lines.mapped('lot_id')[:1] if move_lines else False
                if lot:
                    _logger.warning("Found lot: %s (ID: %s)", lot.name, lot.id)
                else:
                    _logger.warning("No lot found in pickings")
            else:
                _logger.warning("No move lines found in pickings for trade product")
        else:
            _logger.warning("No pickings found for this order")

        product = trade_lines[0].product_id
        trade_vals = {
            'trade_type': 'long',
            'quantity': total_qty,
            'price': avg_price,
            'purchase_currency_id': order.currency_id.id,
            'purchase_date': order.date_order.date() if order.date_order else fields.Date.context_today(self),
            'purchase_id': order.id,
            'status': 'confirmed',
            'product_id': product.id,
        }
        _logger.warning(f"Setting product to: {product.name}")

        if lot:
            trade_vals['lot_ids'] = [(4, lot.id)]
            _logger.warning(f"Adding lot {lot.name} to trade")

        _logger.warning("Creating new trade with values: %s", trade_vals)
        return trade_vals

    def _trading_purchase_bridge_create(self, vals):
        """Create a new trade record with the given values. This method is called when no existing trade is found for the purchase order."""
        order = self
        try:
            return self._bridge_default_create('trading.trade', vals)
        except (ValueError, KeyError, AttributeError, UserError, ValidationError) as e:
            _logger.error('Error creating trade: %s', str(e))
            _logger.error('Traceback:', exc_info=True)
            order.message_post(body=_(
                """
                Error creating trade:
                %(error)s
                Please create the trade manually.
                """,
                error=str(e),
            ))
            return self.env['trading.trade']

    def _trading_purchase_bridge_link(self, group, record):
        self.trade_id = record.id

    def action_view_trade(self):
        """Action to view the related trade"""
        self.ensure_one()
        if not self.trade_id:
            return False

        return {
            'type': 'ir.actions.act_window',
            'name': 'Trade',
            'res_model': 'trading.trade',
            'view_mode': 'form',
            'res_id': self.trade_id.id,
            'target': 'current',
        }
