import logging
from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class TradingTradeMargin(models.Model):
    """Target margin tracking. Lets a trader set an intended profit margin on a
    trade at setup, then compares actual realized+unrealized P&L against that
    target. Purely a comparison layer -- has no effect on pricing, sales, or the
    existing P&L calculations in trading_trade_pnl.py.

    Long and short trades are handled differently, because whichever side of
    the trade already has real numbers is different:
    - Long: you bought first, cost is known -- solve for the target SALE price.
    - Short: you sold first, revenue is known -- solve for the target
      PURCHASE/COVER price.
    """
    _inherit = 'trading.trade'

    ele_target_margin_percent = fields.Float(
        string='Target Margin %',
        default=0.0,
        help='The profit margin you intend to make on this trade, as a percentage '
             'over cost. Purely informational -- does not affect pricing or actual '
             'P&L, only the target comparison fields below.'
    )

    ele_target_pnl = fields.Monetary(
        string='Target P&L',
        compute='_compute_target_margin_fields',
        store=True,
        currency_field='currency_id',
        help='The P&L you would expect if this trade hit your Target Margin %. '
             'For long trades, based on total cost (purchase cost + additional '
             'costs). For short trades, based on total sale proceeds (sales value '
             '+ additional revenue), since the cost side may not exist yet.'
    )

    ele_target_sales_price = fields.Monetary(
        string='Target Sales Price',
        compute='_compute_target_margin_fields',
        store=True,
        currency_field='currency_id',
        help='Long trades only: the per-unit sale price needed to hit your Target '
             'Margin %, given the average cost per unit. Compare against Sales '
             'Price / Avg Sale Price.'
    )

    ele_target_purchase_price = fields.Monetary(
        string='Target Purchase Price',
        compute='_compute_target_margin_fields',
        store=True,
        currency_field='currency_id',
        help='Short trades only: the most you can pay to cover this position and '
             'still hit your Target Margin %, given the average sale price already '
             'locked in. Compare against Purchase Price once you buy to cover.'
    )

    ele_margin_pnl_variance = fields.Monetary(
        string='Margin Variance',
        compute='_compute_target_margin_fields',
        store=True,
        currency_field='currency_id',
        help='Total P&L - Target P&L. Positive means you are beating your '
             'intended margin; negative means you are falling short of it.'
    )

    ele_margin_pnl_variance_percent = fields.Float(
        string='Margin Variance %',
        compute='_compute_target_margin_fields',
        store=True,
        help='Margin Variance expressed as a percentage of Target P&L. '
             'Blank/zero if no Target Margin % has been set.'
    )

    @api.depends('ele_target_margin_percent', 'ele_trade_type', 'ele_total_purchase_cost',
                 'ele_additional_costs', 'ele_total_sales_value', 'ele_additional_revenue',
                 'quantity', 'ele_total_sold_quantity', 'ele_total_pnl')
    def _compute_target_margin_fields(self):
        for record in self:
            margin_fraction = (record.ele_target_margin_percent / 100.0) if record.ele_target_margin_percent else 0.0

            record.ele_target_sales_price = 0.0
            record.ele_target_purchase_price = 0.0

            if record.ele_trade_type == 'long':
                cost_basis = record.ele_total_purchase_cost + record.ele_additional_costs
                avg_cost_per_unit = (cost_basis / record.quantity) if record.quantity else 0.0

                record.ele_target_pnl = cost_basis * margin_fraction if cost_basis > 0 else 0.0

                if margin_fraction and avg_cost_per_unit > 0:
                    record.ele_target_sales_price = avg_cost_per_unit * (1 + margin_fraction)

            else:
                # Short trades: margin is a fraction of revenue, not cost, so
                # ele_target_pnl = margin * cost, and cost = revenue - ele_target_pnl.
                # Substituting and solving for ele_target_pnl gives the /(1+margin)
                # below instead of a plain multiplication.
                revenue_basis = record.ele_total_sales_value + record.ele_additional_revenue
                qty_sold = record.ele_total_sold_quantity or record.quantity
                avg_sale_per_unit = (revenue_basis / qty_sold) if qty_sold else 0.0

                if revenue_basis > 0 and (1 + margin_fraction) != 0:
                    record.ele_target_pnl = revenue_basis * margin_fraction / (1 + margin_fraction)
                else:
                    record.ele_target_pnl = 0.0

                if margin_fraction and avg_sale_per_unit > 0 and (1 + margin_fraction) != 0:
                    record.ele_target_purchase_price = avg_sale_per_unit / (1 + margin_fraction)

            record.ele_margin_pnl_variance = record.ele_total_pnl - record.ele_target_pnl

            if record.ele_target_pnl:
                record.ele_margin_pnl_variance_percent = (record.ele_margin_pnl_variance / abs(record.ele_target_pnl)) * 100.0
            else:
                record.ele_margin_pnl_variance_percent = 0.0

            _logger.info(
                f"target margin check {record.name} ({record.ele_trade_type}): "
                f"target_margin={record.ele_target_margin_percent}% ele_target_pnl={record.ele_target_pnl} "
                f"actual_pnl={record.ele_total_pnl} variance={record.ele_margin_pnl_variance}"
            )