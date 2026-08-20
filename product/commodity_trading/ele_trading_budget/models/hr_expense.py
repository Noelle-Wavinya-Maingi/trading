# -*- coding: utf-8 -*-
from odoo import api, fields, models


class HrExpenseTrade(models.Model):
    """Link expenses to a trade. ele_budget_line_id itself (and its generic amount-sync)
    comes from the budgets_hr_expense module's hr.expense extension -- this only adds
    ele_trade_id and the freight-equivalent UX (domain narrowing + clearing ele_budget_line_id
    on trade change)."""
    _inherit = 'hr.expense'

    ele_trade_id = fields.Many2one(
        'trading.trade',
        string='Trade',
        help='Trade this expense is related to',
        tracking=True,
        index=True,
    )

    ele_budget_line_id = fields.Many2one(
        domain="[('ele_trade_id', '=', ele_trade_id), ('expense_id', '=', False)]",
    )

    def _budget_anchor_providers(self):
        return super()._budget_anchor_providers() + [{
            'field': 'ele_trade_id',
            'get_from_budget_line': lambda line: line.ele_trade_id or False,
        }]

    @api.onchange('ele_trade_id')
    def _onchange_trade_id(self):
        """Clear ele_budget_line_id when ele_trade_id changes."""
        if self.ele_trade_id != self._origin.ele_trade_id:
            self.ele_budget_line_id = False
