# -*- coding: utf-8 -*-
from odoo import fields, models


class TradingTradeBudgetLine(models.Model):
    """Trading-specific extension of the shared operations.budget.line: adds the
    ele_trade_budget_id anchor (the trading.trade.budget header -- one per trade) and pushes
    actual amounts into the trade's existing additional_costs/additional_revenue
    ledger (the same fields already maintained by account_move_trade_pnl.py /
    account_move_lifecycle.py for invoice/bill-driven P&L).
    """
    _inherit = 'operations.budget.line'

    ele_trade_budget_id = fields.Many2one(
        'trading.trade.budget',
        # Not required: a freight-only line has no trade budget, and a NOT
        # NULL here breaks the moment both verticals coexist (it broke
        # exactly that way once).
        string='Trade Budget',
        ondelete='cascade',
        index=True
    )
    ele_trade_id = fields.Many2one(
        'trading.trade',
        string='Trade',
        related='ele_trade_budget_id.ele_trade_id',
        store=True,
        index=True
    )

    ele_pnl_contributed_amount = fields.Float(default=0.0)
    ele_pnl_contributed_field = fields.Char(default=False)

    # Registered, not overridden directly -- omni_budget extends this same
    # model with its own anchor, and a plain override would collide with it.
    def _anchor_providers(self):
        return super()._anchor_providers() + [{
            'owns_line': lambda: bool(self.ele_trade_budget_id),
            'anchor_record': self._trading_anchor_record,
            'anchor_link_vals': self._trading_anchor_link_vals,
            'display_name_prefix': self._trading_anchor_display_name_prefix,
            'notify_amount_change': self._trading_anchor_notify_amount_change,
            'conversion_company': self._trading_anchor_conversion_company,
            'target_currency': self._trading_anchor_target_currency,
        }]

    # The trade budget header IS this line's anchor record.
    def _trading_anchor_record(self):
        return self.ele_trade_budget_id

    # Lets a backend (e.g. an hr.expense) link back to the trade.
    def _trading_anchor_link_vals(self):
        if not self.ele_trade_id:
            return {}
        return {'ele_trade_id': self.ele_trade_id.id}

    # Used to prefix the auto-generated expense name with the trade number.
    def _trading_anchor_display_name_prefix(self):
        return self.ele_trade_id.name or ''

    # Falls back to the current company if the anchor is missing/unset.
    def _trading_anchor_conversion_company(self):
        return self.ele_trade_id.company_id or self.env.company

    # Falls back to the line's own currency if the trade has none.
    def _trading_anchor_target_currency(self):
        return self.ele_trade_id.currency_id or self.currency_id

    # Push this line's amount into the trade's P&L ledger.
    def _trading_anchor_notify_amount_change(self):
        self._sync_pnl_contribution()

    def _get_pnl_target(self):
        self.ensure_one()
        if not self.ele_trade_id or self.account_move_id:
            return None
        if self.line_type == 'expense':
            return ('ele_additional_costs', self.actual_amount)
        if self.line_type == 'other':
            return ('ele_additional_costs', -self.actual_amount)
        if self.line_type == 'charge':
            return ('ele_additional_revenue', self.actual_amount)
        return None

    def _sync_pnl_contribution(self):
        for line in self:
            if not isinstance(line.id, int):
                continue
            trade = line.ele_trade_id
            if not trade:
                continue

            if line.ele_pnl_contributed_amount and line.ele_pnl_contributed_field:
                current = trade[line.ele_pnl_contributed_field]
                trade.write({line.ele_pnl_contributed_field: max(current - line.ele_pnl_contributed_amount, 0.0)})

            target = line._get_pnl_target()
            bookkeeping_vals = {'ele_pnl_contributed_amount': 0.0, 'ele_pnl_contributed_field': False}
            if target:
                field_name, amount = target
                current = trade[field_name]
                trade.write({field_name: current + amount})
                bookkeeping_vals = {'ele_pnl_contributed_amount': amount, 'ele_pnl_contributed_field': field_name}

            if (line.ele_pnl_contributed_amount, line.ele_pnl_contributed_field) != (
                bookkeeping_vals['ele_pnl_contributed_amount'], bookkeeping_vals['ele_pnl_contributed_field']
            ):
                line.sudo().with_context(skip_expense_update=True).write(bookkeeping_vals)

            trade._compute_all_trade_fields()

    def unlink(self):
        for line in self:
            trade = line.ele_trade_id
            if trade and line.ele_pnl_contributed_amount and line.ele_pnl_contributed_field:
                current = trade[line.ele_pnl_contributed_field]
                trade.write({line.ele_pnl_contributed_field: max(current - line.ele_pnl_contributed_amount, 0.0)})
                trade._compute_all_trade_fields()
        return super().unlink()