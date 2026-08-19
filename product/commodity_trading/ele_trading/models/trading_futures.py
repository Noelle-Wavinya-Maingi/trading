import logging
from odoo import models, fields, api

_logger = logging.getLogger(__name__)

class TradingFutures(models.Model):
    _name = 'trading.futures'
    _description = 'Trading Futures'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'ele_trade_id, ele_open_date, id'  # Add default ordering

    name = fields.Char(string='Future Name', copy=False, compute='_compute_name', store=True)
    ele_trade_id = fields.Many2one('trading.trade', string='Trade', required=True, ondelete='cascade')
    ele_contract_type = fields.Selection([('cocoa_future','Cocoa Future')], string='Contract Type', default='cocoa_future')
    ele_contract_price = fields.Float(string='Contract Price', required=True, digits=(16, 2))
    ele_contract_quantity = fields.Float(string='Contract Quantity', required=True, digits=(16, 2))
    ele_open_date = fields.Date(string='Open Date', required=True, default=fields.Date.today)
    ele_close_date = fields.Date(string='Close Date')
    ele_status = fields.Selection([('open','Open'),('closed','Closed')], default='open', tracking=True)
    currency_id = fields.Many2one(related="ele_trade_id.currency_id", store=True)
    ele_product_uom = fields.Many2one(related="ele_trade_id.ele_product_uom", store=True, readonly=True)

    # P&L fields
    ele_pnl = fields.Float(
        string='P&L',
        compute='_compute_pnl',
        store=True,
        digits=(16, 2),
        help='Profit and Loss'
    )

    ele_pnl_percentage = fields.Float(
        string='P&L %',
        compute='_compute_pnl',
        store=True,
        digits=(16, 2),
        help='Profit and Loss Percentage'
    )

    ele_current_price = fields.Float(
        string='Current/Market Price',
        help='Current market price for open positions',
        digits=(16, 2),
        default=lambda self: self._get_default_current_price(),
        tracking=True
    )

    # Delivery Tracking
    ele_delivered_quantity = fields.Float(
        string='Delivered Quantity',
        default=0.0,
        digits=(16, 2),
        help='Total quantity delivered against this future'
    )

    # Balance Fields
    ele_open_balance = fields.Float(
        string='Open Balance',
        compute='_compute_balances',
        store=True,
        digits=(16, 2),
        help='Remaining quantity to be delivered'
    )

    ele_closed_balance = fields.Float(
        string='Closed Balance',
        compute='_compute_balances',
        store=True,
        digits=(16, 2),
        help='Quantity already delivered'
    )

    # Value Fields at Contract Price
    ele_closed_value_at_contract = fields.Float(
        string='Closed Value (Contract)',
        compute='_compute_values',
        store=True,
        digits=(16, 2),
        help='Value of delivered portion at contract price'
    )

    ele_open_value_at_contract = fields.Float(
        string='Open Value (Contract)',
        compute='_compute_values',
        store=True,
        digits=(16, 2),
        help='Value of undelivered portion at contract price'
    )

    ele_total_contract_value = fields.Float(
        string='Total Contract Value',
        compute='_compute_values',
        store=True,
        digits=(16, 2),
        help='Total contract value (Quantity × Price)'
    )

    # Actual Sales Values (from sale orders, not deliveries)
    ele_closed_sales_value = fields.Float(
        string='Closed Sales Value',
        compute='_compute_sales_values',
        store=True,
        digits=(16, 2),
        help='Actual sales value from confirmed sale orders'
    )

    # Net Value (actual sales value + open balance × contract price)
    ele_net_value = fields.Float(
        string='Net Value',
        compute='_compute_net_value',
        store=True,
        digits=(16, 2),
        help='Actual value: (Sales value) + (Open at contract price)'
    )

    # Realized/Unrealized P&L
    ele_realized_pnl = fields.Float(
        string='Realized P&L',
        compute='_compute_pnl_details',
        store=True,
        digits=(16, 2),
        help='Profit/Loss on sold portion (based on sale orders)'
    )

    ele_unrealized_pnl = fields.Float(
        string='Unrealized P&L',
        compute='_compute_pnl_details',
        store=True,
        digits=(16, 2),
        help='Profit/Loss on open portion (based on current price)'
    )

    # For tracking deliveries with their individual sale prices
    # delivery_line_ids = fields.One2many(
    #     'trading.future.delivery.line',
    #     'ele_future_id',
    #     string='Delivery Lines'
    # )

    # Sale Order relationship
    # ele_sale_order_ids = fields.One2many(
    #     'sale.order',
    #     'futures_id',
    #     string='Sale Orders'
    # )

    # Add a sequence field for ordering
    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help='Sequence for ordering futures under the same trade'
    )

    def _get_default_current_price(self):
        """Get default current price - you can customize this logic"""
        return self.ele_contract_price

    @api.depends('ele_contract_price', 'ele_contract_quantity', 'ele_current_price', 'ele_status',
                 'ele_realized_pnl', 'ele_unrealized_pnl', 'ele_close_date')
    def _compute_pnl(self):
        for record in self:
            if record.ele_status == 'closed':
                # For closed positions, P&L is just the realized P&L
                record.ele_pnl = record.ele_realized_pnl
            else:
                # For open positions, show total P&L (realized + unrealized)
                record.ele_pnl = record.ele_realized_pnl + record.ele_unrealized_pnl

            # Calculate P&L percentage
            total_cost = record.ele_contract_price * record.ele_contract_quantity
            if total_cost != 0:
                record.ele_pnl_percentage = (record.ele_pnl / total_cost) * 100
            else:
                record.ele_pnl_percentage = 0

    @api.depends('ele_contract_quantity', 'ele_delivered_quantity')
    def _compute_balances(self):
        for future in self:
            _logger.info(f"🫠 Computing balances for future {future.name}")
            future.ele_closed_balance = sum(future.ele_sale_order_ids.filtered(lambda so: so.state in ['sale', 'done']).mapped('order_line.product_uom_qty'))
            future.ele_open_balance = future.ele_contract_quantity - future.ele_closed_balance

    @api.depends('ele_contract_quantity', 'ele_contract_price', 'ele_closed_balance', 'ele_open_balance')
    def _compute_values(self):
        for future in self:
            future.ele_total_contract_value = future.ele_contract_quantity * future.ele_contract_price
            future.ele_closed_value_at_contract = future.ele_closed_balance * future.ele_contract_price
            future.ele_open_value_at_contract = future.ele_open_balance * future.ele_contract_price

    @api.depends()
    def _compute_sales_values(self):
        """Compute closed sales value from CONFIRMED sale orders only"""
        for future in self:
            # Only include confirmed/done sale orders
            confirmed_orders = future.ele_sale_order_ids.filtered(lambda so: so.state in ['sale', 'done'])
            future.ele_closed_sales_value = sum(confirmed_orders.mapped('amount_untaxed'))
            _logger.info(f"😎 Sales values computed from {len(confirmed_orders)} confirmed sale orders: {future.ele_closed_sales_value}")

    @api.depends('ele_closed_sales_value', 'ele_open_balance', 'ele_contract_price')
    def _compute_net_value(self):
        for future in self:
            open_value_contract = future.ele_open_balance * future.ele_contract_price
            future.ele_net_value = future.ele_closed_sales_value + open_value_contract

    @api.depends(
                 'ele_closed_balance', 'ele_contract_price', 'ele_current_price')
    def _compute_pnl_details(self):
        for future in self:
            # Realized P&L = Sales Value - (Closed Balance × Contract Price)
            future.ele_realized_pnl = future.ele_closed_sales_value - (future.ele_closed_balance * future.ele_contract_price)

            # Unrealized P&L on open portion
            if future.ele_status == 'open' and future.ele_open_balance > 0:
                if future.ele_trade_id.ele_trade_type == 'long':
                    future.ele_unrealized_pnl = future.ele_open_balance * (future.ele_current_price - future.ele_contract_price)
                else:
                    future.ele_unrealized_pnl = (future.ele_contract_price - future.ele_current_price) * future.ele_open_balance
            else:
                future.ele_unrealized_pnl = 0.0

    @api.depends('ele_trade_id', 'ele_contract_type', 'ele_open_date', 'sequence')
    def _compute_name(self):
        """Generate unique names for futures under the same trade"""
        for record in self:
            if record.ele_trade_id and record.ele_contract_type:
                date_str = record.ele_open_date.strftime('%Y-%m-%d') if record.ele_open_date else ''

                # Count how many futures exist for this trade with the same open date
                domain = [
                    ('ele_trade_id', '=', record.ele_trade_id.id),
                    ('ele_open_date', '=', record.ele_open_date),
                    ('id', '<=', record.id)  # Include current and previous records
                ]

                # Get all futures for this trade with same date
                same_trade_futures = self.search(domain, order='id')

                # Find the index of the current record (1-based)
                index = 1
                for i, future in enumerate(same_trade_futures, 1):
                    if future.id == record.id:
                        index = i
                        break

                # If there are multiple futures with same date, add the index
                if len(same_trade_futures) > 1:
                    record.name = f"{record.ele_trade_id.name} - {record.ele_contract_type} - {date_str} - #{index}"
                else:
                    # Check if there are any other futures for this trade (different dates)
                    other_futures = self.search_count([
                        ('ele_trade_id', '=', record.ele_trade_id.id),
                        ('id', '!=', record.id)
                    ])

                    if other_futures > 0:
                        # If there are other futures for this trade, add a sequence based on creation order
                        all_trade_futures = self.search([('ele_trade_id', '=', record.ele_trade_id.id)], order='id')
                        global_index = 1
                        for i, future in enumerate(all_trade_futures, 1):
                            if future.id == record.id:
                                global_index = i
                                break
                        record.name = f"{record.ele_trade_id.name} - {record.ele_contract_type} - {date_str} - #{global_index}"
                    else:
                        # First/only future for this trade
                        record.name = f"{record.ele_trade_id.name} - {record.ele_contract_type} - {date_str}"
            else:
                record.name = "New Future"

    @api.model_create_multi
    def create(self, vals_list):
        """Set sequence and name on creation"""
        for vals in vals_list:
            if vals.get('ele_trade_id'):
                # Count existing futures for this trade
                future_count = self.search_count([('ele_trade_id', '=', vals['ele_trade_id'])])
                vals['sequence'] = future_count + 1
        return super().create(vals_list)

    def action_close_future(self):
        """Manually close a future"""
        for future in self:
            if future.ele_status == 'open':
                future.write({
                    'ele_status': 'closed',
                    'ele_close_date': fields.Date.today()
                })
                future.message_post(
                    body="Future manually closed.",
                    subject="Future Closed"
                )

    def action_reopen_future(self):
        """Reopen a closed future"""
        for future in self:
            if future.ele_status == 'closed':
                future.write({
                    'ele_status': 'open',
                    'ele_close_date': False
                })
                future.message_post(
                    body="Future reopened.",
                    subject="Future Reopened"
                )

    def write(self, vals):
        """Override write to ensure proper recomputation"""
        result = super().write(vals)

        # If ele_status changed to closed, ensure ele_close_date is set
        if vals.get('ele_status') == 'closed' and not vals.get('ele_close_date'):
            self.write({'ele_close_date': fields.Date.today()})

        # If ele_current_price changed, trigger P&L recomputation
        if 'ele_current_price' in vals:
            self._compute_pnl_details()
            self._compute_pnl()
            _logger.info(f"😃 Current price updated, P&L recomputed for {self.name}")

        # If ele_delivered_quantity changed, trigger recomputation
        if 'ele_delivered_quantity' in vals:
            self._compute_balances()
            self._compute_values()
            self._compute_net_value()
            self._compute_pnl_details()
            self._compute_pnl()

        return result

    @api.onchange('ele_close_date')
    def _onchange_contract_price(self):
        for record in self:
            if record.ele_close_date:
                _logger.info(f"😃 Well i have been triggered.")
