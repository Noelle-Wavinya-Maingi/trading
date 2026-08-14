# -*- coding: utf-8 -*-
from odoo import api, fields, models


class HrExpenseTrade(models.Model):
    """Link expenses to a trade. budget_line_id itself (and its generic amount-sync)
    comes from the budgets_hr_expense module's hr.expense extension -- this only adds
    trade_id and the freight-equivalent UX (domain narrowing + clearing budget_line_id
    on trade change)."""
    _inherit = 'hr.expense'

    trade_id = fields.Many2one(
        'trading.trade',
        string='Trade',
        help='Trade this expense is related to',
        tracking=True,
        index=True,
    )

    budget_line_id = fields.Many2one(
        domain="[('trade_id', '=', trade_id), ('expense_id', '=', False)]",
    )

    def _budget_anchor_providers(self):
        return super()._budget_anchor_providers() + [{
            'field': 'trade_id',
            'get_from_budget_line': lambda line: line.trade_id or False,
        }]

    @api.onchange('trade_id')
    def _onchange_trade_id(self):
        """Clear budget_line_id when trade_id changes."""
        if self.trade_id != self._origin.trade_id:
            self.budget_line_id = False
