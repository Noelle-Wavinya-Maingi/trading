import logging
from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class TradingTradePnl(models.Model):
    """Open position, realized/unrealized P&L, cost basis, and win rate."""
    _inherit = 'trading.trade'

    ele_total_sold_quantity = fields.Float(
        string='Total Sold Quantity',
        compute='_compute_sales_totals',
        store=True,
        help='Total quantity sold across all sale orders'
    )

    ele_total_sales_value = fields.Monetary(
        string='Total Sales Value',
        compute='_compute_sales_totals',
        store=True,
        currency_field='currency_id',
        help='Total value of all sales, converted to reporting currency at each order date'
    )

    ele_average_sale_price = fields.Monetary(
        string='Average Sale Price',
        compute='_compute_sales_totals',
        store=True,
        currency_field='currency_id',
        help='Average price per unit from all sales, in reporting currency'
    )

    ele_open_position_quantity = fields.Float(
        string='Open Position Quantity',
        compute='_compute_position',
        store=True,
        help='Net open position: Purchase Qty - Sold Qty (positive = long, negative = short)'
    )

    ele_is_fully_matched = fields.Boolean(
        string='Fully Matched',
        compute='_compute_position',
        store=True,
        help='Both purchase and sale exist and quantities match (position closed)'
    )

    ele_realized_pnl = fields.Monetary(
        string='Realized P&L',
        compute='_compute_pnl',
        store=True,
        currency_field='currency_id',
        help='Profit/Loss on matched portion (when both purchase and sale exist)'
    )

    ele_unrealized_pnl = fields.Monetary(
        string='Unrealized P&L',
        compute='_compute_pnl',
        store=True,
        currency_field='currency_id',
        help='Profit/Loss on unmatched portion (open position)'
    )

    ele_total_pnl = fields.Monetary(
        string='Total P&L',
        compute='_compute_pnl',
        store=True,
        currency_field='currency_id',
        help='Total Profit/Loss (Realized + Unrealized + Additional Revenue)'
    )

    ele_pnl_percentage = fields.Float(
        string='P&L %',
        compute='_compute_pnl',
        store=True,
        help='Profit/Loss Percentage'
    )

    ele_total_purchase_cost = fields.Monetary(
        string='Total Purchase Cost',
        compute='_compute_costs',
        store=True,
        currency_field='currency_id',
        help='Total cost of purchase in reporting currency (Quantity × Purchase Price converted)'
    )

    ele_total_sales_cost_basis = fields.Monetary(
        string='Total Sales Cost Basis',
        compute='_compute_costs',
        store=True,
        currency_field='currency_id',
        help='Cost basis for sold items in reporting currency (Sold Qty × Purchase Price converted)'
    )
    
    ele_open_position_cost_basis = fields.Monetary(
        string='Open Position Cost Basis',
        compute='_compute_costs',
        store=True,
        currency_field='currency_id',
        help='Cost basis for sold items in reporting currency'
    )

    ele_win_rate = fields.Boolean(
        string='Profitable',
        compute='_compute_performance',
        store=True,
        help='Whether this trade closed with a positive realized P&L'
    )

    @api.depends('quantity', 'ele_total_sold_quantity', 'ele_purchase_id', 'ele_sale_order_ids', 'ele_sale_order_ids.state')
    def _compute_position(self):
        """Calculate open position and check if fully matched."""
        for record in self:
            has_purchase_doc = bool(record.ele_purchase_id)
            has_sale_docs = bool(record.ele_sale_order_ids.filtered(lambda so: so.state in ['sale', 'done']))

            if has_purchase_doc and not has_sale_docs:
                open_qty = record.quantity
                _logger.info(f"Only purchase: LONG position of {open_qty}")
            elif has_sale_docs and not has_purchase_doc:
                open_qty = -record.ele_total_sold_quantity
            elif has_purchase_doc and has_sale_docs:
                open_qty = record.quantity - record.ele_total_sold_quantity
            else:
                open_qty = 0

            record.ele_open_position_quantity = open_qty
            has_purchase = has_purchase_doc and record.quantity > 0
            has_sale = has_sale_docs and record.ele_total_sold_quantity > 0
            quantities_match = abs(open_qty) < 0.001 if has_purchase and has_sale else False
            record.ele_is_fully_matched = has_purchase and has_sale and quantities_match

    @api.depends('ele_total_sales_value', 'ele_total_sales_cost_basis', 'ele_open_position_quantity', 'ele_current_price', 'ele_trade_type', 'quantity', 'ele_total_sold_quantity', 'ele_additional_costs', 'ele_additional_revenue', 'ele_price_in_base_currency', 'ele_sales_price_in_base_currency')
    def _compute_pnl(self):
        """Calculate P&L using ele_price_in_base_currency so FX is applied correctly."""
        for record in self:
            has_purchase_doc = bool(record.ele_purchase_id) and record.quantity > 0
            has_sale_docs = (bool(record.ele_sale_order_ids.filtered(lambda so: so.state in ['sale', 'done'])) and record.ele_total_sold_quantity > 0)

            # Average cost per unit in reporting currency, including additional costs
            avg_cost_per_unit = 0.0
            if record.quantity > 0:
                total_cost = (record.quantity * record.ele_price_in_base_currency) + record.ele_additional_costs
                avg_cost_per_unit = total_cost / record.quantity

            # REALIZED P&L
            if has_purchase_doc and has_sale_docs:
                matched_qty = min(record.quantity, record.ele_total_sold_quantity)
                # ele_total_sales_value is already converted to reporting currency
                # per order at its own date (see _compute_sales_totals)
                record.ele_realized_pnl = record.ele_total_sales_value - (matched_qty * avg_cost_per_unit)
            else:
                record.ele_realized_pnl = 0.0

            # UNREALIZED P&L — only when market price is set
            if record.ele_open_position_quantity != 0 and record.ele_current_price > 0:
                open_qty = abs(record.ele_open_position_quantity)

                if record.ele_open_position_quantity > 0:
                    # LONG
                    if avg_cost_per_unit > 0:
                        record.ele_unrealized_pnl = open_qty * (record.ele_current_price - avg_cost_per_unit)
                    else:
                        record.ele_unrealized_pnl = 0.0
                else:
                    # SHORT
                    sale_price_to_use = (record.ele_sales_price_in_base_currency if record.ele_sales_price_in_base_currency > 0 else record.ele_average_sale_price)
                    if sale_price_to_use > 0:
                        record.ele_unrealized_pnl = open_qty * (sale_price_to_use - record.ele_current_price)
                        _logger.info(f"SHORT Unrealized P&L: {open_qty} * "f"({sale_price_to_use} - {record.ele_current_price}) = {record.ele_unrealized_pnl}")
                    else:
                        record.ele_unrealized_pnl = 0.0
            elif record.ele_open_position_quantity != 0:
                # Open position but no market price — show cost exposure for LONG,
                # zero for SHORT (we don't know what it costs to cover yet)
                if record.ele_open_position_quantity > 0 and avg_cost_per_unit > 0:
                    record.ele_unrealized_pnl = -(abs(record.ele_open_position_quantity) * avg_cost_per_unit)
                else:
                    record.ele_unrealized_pnl = 0.0
            else:
                record.ele_unrealized_pnl = 0.0

            # TOTAL P&L
            record.ele_total_pnl = record.ele_realized_pnl + record.ele_unrealized_pnl + record.ele_additional_revenue

            _logger.debug(f"TOTAL P&L = {record.ele_total_pnl} "f"(realized={record.ele_realized_pnl} + unrealized={record.ele_unrealized_pnl} "f"+ ele_additional_revenue={record.ele_additional_revenue})"f"[{record.currency_id.name if record.currency_id else'N/A'}]")

            # P&L PERCENTAGE
            if record.ele_trade_type == 'long':
                total_cost_base = (record.quantity * record.ele_price_in_base_currency) + record.ele_additional_costs 
                record.ele_pnl_percentage = ((record.ele_total_pnl / total_cost_base) * 100 if total_cost_base > 0 else 0.0)
            elif record.ele_trade_type == 'short':
                total_revenue_base = record.ele_total_sales_value + record.ele_additional_revenue
                record.ele_pnl_percentage = ((record.ele_total_pnl / total_revenue_base) * 100 if total_revenue_base > 0 else 0.0)
            else:
                record.ele_pnl_percentage = 0.0

    @api.depends('ele_sale_order_ids', 'ele_sale_order_ids.state', 'ele_sale_order_ids.order_line', 'ele_sale_order_ids.currency_id', 'ele_sale_order_ids.date_order', 'currency_id')
    def _compute_sales_totals(self):
        """Compute sales totals only."""
        for record in self:
            confirmed_orders = record.ele_sale_order_ids.filtered(lambda so: so.state in ['sale', 'done'])
            company = record.company_id or self.env.company
            total_qty = 0.0
            total_value = 0.0

            for order in confirmed_orders:
                order_currency = order.currency_id or record.currency_id
                rate_date = (order.date_order.date() if order.date_order else fields.Date.context_today(record))
                for line in order.order_line:
                    if line.product_id == record.product_id:
                        qty = line.product_uom_qty
                        line_value = line.price_unit * qty
                        if order_currency != record.currency_id:
                            line_value = order_currency._convert(line_value, record.currency_id, company, rate_date)
                            _logger.info(f" {record.name}: Sale line converted"f"({order_currency.name} → {record.currency_id.name} at {rate_date})")
                        total_qty += qty
                        total_value += line_value

            record.ele_total_sold_quantity = total_qty
            record.ele_total_sales_value = total_value
            record.ele_average_sale_price = total_value / total_qty if total_qty > 0 else 0.0

            _logger.info(f" {record.name}: Sales — Qty: {total_qty},"f"Value: {total_value} {record.currency_id.name if record.currency_id else''},"f"Avg: {record.ele_average_sale_price}")

    @api.depends('quantity', 'ele_price_in_base_currency', 'ele_total_sold_quantity')
    def _compute_costs(self):
        """Compute purchase costs and sales cost basis in reporting currency."""
        for record in self:
            if record.quantity > 0 and record.ele_price_in_base_currency > 0:
                record.ele_total_purchase_cost = record.quantity * record.ele_price_in_base_currency
                record.ele_total_sales_cost_basis = record.ele_total_sold_quantity * record.ele_price_in_base_currency
                record.ele_open_position_cost_basis = abs(record.ele_open_position_quantity) * record.ele_price_in_base_currency
            else:
                record.ele_total_purchase_cost = 0.0
                record.ele_total_sales_cost_basis = 0.0
                record.ele_open_position_cost_basis = 0.0

    @api.depends('ele_sale_order_ids', 'ele_sale_order_ids.state', 'ele_sale_order_ids.order_line', 'price')
    def _compute_performance(self):
        for record in self:
            record.ele_win_rate = record.ele_realized_pnl > 0
