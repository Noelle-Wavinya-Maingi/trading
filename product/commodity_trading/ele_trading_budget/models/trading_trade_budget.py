# -*- coding: utf-8 -*-
from odoo import api, fields, models


class TradingTradeBudget(models.Model):
    """Budget header for a trade. Exactly one per trade."""
    _name = 'trading.trade.budget'
    _description = 'Trade Budget'
    _order = 'create_date desc'
    _rec_name = 'name'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'budget.document.mixin']

    _trade_uniq = models.Constraint('unique(ele_trade_id)', 'A trade can only have one budget.')

    ele_trade_id = fields.Many2one(
        'trading.trade',
        string='Trade',
        required=True,
        ondelete='cascade',
        index=True
    )
    ele_trade_type = fields.Selection(
        related='ele_trade_id.ele_trade_type',
        string='Trade Type',
        store=True,
        readonly=True
    )

    ele_is_fully_matched = fields.Boolean(
        related='ele_trade_id.ele_is_fully_matched',
        readonly=True,
    )
    ele_analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string='Analytic Account',
        tracking=True,
        help='Optional analytic account for future accounting integration'
    )

    ele_budget_line_ids = fields.One2many(
        'operations.budget.line',
        'ele_trade_budget_id',
        string='Budget Lines'
    )

    # === BUDGETED (PLANNED) ===
    ele_total_budgeted_cost = fields.Monetary(
        string='Budgeted Cost',
        compute='_compute_budgeted_totals',
        store=True,
        currency_field='currency_id',
        help='Sum of budgeted_amount across Cost/Other budget lines'
    )
    ele_total_budgeted_revenue = fields.Monetary(
        string='Budgeted Revenue',
        compute='_compute_budgeted_totals',
        store=True,
        currency_field='currency_id',
        help='Sum of budgeted_amount across Revenue budget lines'
    )

    # === ACTUAL (from the trade's own additional_costs/additional_revenue ledger) ===
    ele_actual_cost = fields.Monetary(
        string='Actual Cost',
        compute='_compute_actuals',
        currency_field='currency_id',
        help='The trade\'s Additional Costs -- kept in sync by the budget lines themselves '
             '(and by any invoices/bills linked directly to the trade)'
    )
    ele_actual_revenue = fields.Monetary(
        string='Actual Revenue',
        compute='_compute_actuals',
        currency_field='currency_id',
        help='The trade\'s Additional Revenue -- kept in sync by the budget lines themselves '
             '(and by any invoices/bills linked directly to the trade)'
    )
    ele_cost_variance = fields.Monetary(
        string='Cost Variance',
        compute='_compute_variances',
        store=True,
        currency_field='currency_id',
        help='Actual Cost minus Budgeted Cost -- positive means over budget'
    )
    ele_revenue_variance = fields.Monetary(
        string='Revenue Variance',
        compute='_compute_variances',
        store=True,
        currency_field='currency_id',
        help='Actual Revenue minus Budgeted Revenue'
    )
    
    ele_target_margin_percent = fields.Float(
        related='ele_trade_id.ele_target_margin_percent',
        readonly=True
    )

    ele_target_pnl = fields.Monetary(related='ele_trade_id.ele_target_pnl', readonly=True, currency_field='currency_id')
    ele_total_pnl = fields.Monetary(related='ele_trade_id.ele_total_pnl', readonly=True, currency_field='currency_id', string='Realized Margin')
    ele_margin_pnl_variance = fields.Monetary(related='ele_trade_id.ele_margin_pnl_variance', readonly=True, currency_field='currency_id')
    ele_margin_pnl_variance_percent = fields.Float(related='ele_trade_id.ele_margin_pnl_variance_percent', readonly=True)

    @api.depends('ele_trade_id.ele_total_purchase_cost', 'ele_trade_id.ele_additional_costs', 'ele_trade_id.ele_total_sales_value', 'ele_trade_id.ele_additional_revenue')
    def _compute_actuals(self):
        for budget in self:
            trade = budget.ele_trade_id
            budget.ele_actual_cost = trade.ele_total_purchase_cost + trade.ele_additional_costs
            budget.ele_actual_revenue = trade.ele_total_sales_value + trade.ele_additional_revenue

    @api.depends('ele_budget_line_ids.budgeted_amount', 'ele_budget_line_ids.line_type', 'ele_trade_id.ele_trade_type', 'ele_trade_id.quantity', 'ele_trade_id.price', 'ele_trade_id.ele_sales_price', 'ele_trade_id.ele_target_margin_percent')
    def _compute_budgeted_totals(self):
        for budget in self:
            cost_lines = budget.ele_budget_line_ids.filtered(lambda l: l.line_type in ('expense', 'other'))
            revenue_lines = budget.ele_budget_line_ids.filtered(lambda l: l.line_type == 'charge')
            line_cost = sum(cost_lines.mapped('budgeted_amount'))
            line_revenue = sum(revenue_lines.mapped('budgeted_amount'))
            
            trade = budget.ele_trade_id
            margin_fraction = (trade.ele_target_margin_percent / 100.0) if trade.ele_target_margin_percent else 0.0

            quoted_cost = 0.0
            quoted_revenue = 0.0

            if trade.ele_trade_type == 'long':

                quoted_cost = trade.ele_price_in_base_currency * trade.quantity

                if margin_fraction:
                    quoted_revenue = quoted_cost * (1 + margin_fraction)

            elif trade.ele_trade_type == 'short':

                quoted_revenue = trade.ele_sales_price_in_base_currency * trade.quantity
                
                if margin_fraction and (1 + margin_fraction) != 0:
                    quoted_cost = quoted_revenue / (1 + margin_fraction)
                    
                        
            budget.ele_total_budgeted_cost = line_cost or quoted_cost
            
            budget.ele_total_budgeted_revenue = line_revenue or quoted_revenue
            
            

    @api.depends('ele_total_budgeted_cost', 'ele_total_budgeted_revenue', 'ele_trade_id.ele_additional_costs', 'ele_trade_id.ele_additional_revenue')
    def _compute_variances(self):
        for budget in self:
            budget.ele_cost_variance = budget.ele_actual_cost - budget.ele_total_budgeted_cost
            budget.ele_revenue_variance = budget.ele_actual_revenue - budget.ele_total_budgeted_revenue

    def _budget_sequence_code(self):
        return 'trading.budget'