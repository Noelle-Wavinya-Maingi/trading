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
    trade_type = fields.Selection(
        related='ele_trade_id.trade_type',
        string='Trade Type',
        store=True,
        readonly=True
    )
    
    is_fully_matched = fields.Boolean(
        related='ele_trade_id.is_fully_matched',
        readonly=True,
    )
    analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string='Analytic Account',
        tracking=True,
        help='Optional analytic account for future accounting integration'
    )

    budget_line_ids = fields.One2many(
        'operations.budget.line',
        'trade_budget_id',
        string='Budget Lines'
    )

    # === BUDGETED (PLANNED) ===
    total_budgeted_cost = fields.Monetary(
        string='Budgeted Cost',
        compute='_compute_budgeted_totals',
        store=True,
        currency_field='currency_id',
        help='Sum of budgeted_amount across Cost/Other budget lines'
    )
    total_budgeted_revenue = fields.Monetary(
        string='Budgeted Revenue',
        compute='_compute_budgeted_totals',
        store=True,
        currency_field='currency_id',
        help='Sum of budgeted_amount across Revenue budget lines'
    )

    # === ACTUAL (from the trade's own additional_costs/additional_revenue ledger) ===
    actual_cost = fields.Monetary(
        string='Actual Cost',
        compute='_compute_actuals',
        currency_field='currency_id',
        help='The trade\'s Additional Costs -- kept in sync by the budget lines themselves '
             '(and by any invoices/bills linked directly to the trade)'
    )
    actual_revenue = fields.Monetary(
        string='Actual Revenue',
        compute='_compute_actuals',
        currency_field='currency_id',
        help='The trade\'s Additional Revenue -- kept in sync by the budget lines themselves '
             '(and by any invoices/bills linked directly to the trade)'
    )
    cost_variance = fields.Monetary(
        string='Cost Variance',
        compute='_compute_variances',
        store=True,
        currency_field='currency_id',
        help='Actual Cost minus Budgeted Cost -- positive means over budget'
    )
    revenue_variance = fields.Monetary(
        string='Revenue Variance',
        compute='_compute_variances',
        store=True,
        currency_field='currency_id',
        help='Actual Revenue minus Budgeted Revenue'
    )
    
    target_margin_percent = fields.Float(
        related='ele_trade_id.target_margin_percent',
        readonly=True
    )
    
    target_pnl = fields.Monetary(related='ele_trade_id.target_pnl', readonly=True, currency_field='currency_id')
    total_pnl = fields.Monetary(related='ele_trade_id.total_pnl', readonly=True, currency_field='currency_id', string='Realized Margin')
    margin_pnl_variance = fields.Monetary(related='ele_trade_id.margin_pnl_variance', readonly=True, currency_field='currency_id')
    margin_pnl_variance_percent = fields.Float(related='ele_trade_id.margin_pnl_variance_percent', readonly=True)

    @api.depends('ele_trade_id.total_purchase_cost', 'ele_trade_id.additional_costs', 'ele_trade_id.total_sales_value', 'ele_trade_id.additional_revenue')
    def _compute_actuals(self):
        for budget in self:
            trade = budget.ele_trade_id
            budget.actual_cost = trade.total_purchase_cost + trade.additional_costs
            budget.actual_revenue = trade.total_sales_value + trade.additional_revenue
    
    @api.depends('budget_line_ids.budgeted_amount', 'budget_line_ids.line_type', 'ele_trade_id.trade_type', 'ele_trade_id.quantity', 'ele_trade_id.price', 'ele_trade_id.sales_price', 'ele_trade_id.target_margin_percent')
    def _compute_budgeted_totals(self):
        for budget in self:
            cost_lines = budget.budget_line_ids.filtered(lambda l: l.line_type in ('expense', 'other'))
            revenue_lines = budget.budget_line_ids.filtered(lambda l: l.line_type == 'charge')
            line_cost = sum(cost_lines.mapped('budgeted_amount'))
            line_revenue = sum(revenue_lines.mapped('budgeted_amount'))
            
            trade = budget.ele_trade_id
            margin_fraction = (trade.target_margin_percent / 100.0) if trade.target_margin_percent else 0.0
            
            quoted_cost = 0.0
            quoted_revenue = 0.0
            
            if trade.trade_type == 'long':
                
                quoted_cost = trade.price_in_base_currency * trade.quantity
                
                if margin_fraction:
                    quoted_revenue = quoted_cost * (1 + margin_fraction)
                
            elif trade.trade_type == 'short':
                
                quoted_revenue = trade.sales_price_in_base_currency * trade.quantity
                
                if margin_fraction and (1 + margin_fraction) != 0:
                    quoted_cost = quoted_revenue / (1 + margin_fraction)
                    
                        
            budget.total_budgeted_cost = line_cost or quoted_cost
            
            budget.total_budgeted_revenue = line_revenue or quoted_revenue
            
            

    @api.depends('total_budgeted_cost', 'total_budgeted_revenue', 'ele_trade_id.additional_costs', 'ele_trade_id.additional_revenue')
    def _compute_variances(self):
        for budget in self:
            budget.cost_variance = budget.actual_cost - budget.total_budgeted_cost
            budget.revenue_variance = budget.actual_revenue - budget.total_budgeted_revenue

    def _budget_sequence_code(self):
        return 'trading.budget'