# -*- coding: utf-8 -*-
from odoo import fields, models


class TradingTradeBudgetLine(models.Model):
    """Trading-specific extension of the shared operations.budget.line: adds the
    trade_budget_id anchor (the trading.trade.budget header -- one per trade) and pushes
    actual amounts into the trade's existing additional_costs/additional_revenue
    ledger (the same fields already maintained by account_move_trade_pnl.py /
    account_move_lifecycle.py for invoice/bill-driven P&L).
    """
    _inherit = 'operations.budget.line'

    trade_budget_id = fields.Many2one(
        'trading.trade.budget',
        # Distinct from omni_budget's mrp_budget_id label: two fields on the same
        # model sharing a label makes Odoo warn and makes the UI ambiguous.
        #
        # Not required: operations.budget.line is a shared table -- when
        # omni_budget is also installed, a freight-only line has no trade
        # budget at all, and a NOT NULL constraint here would break every
        # freight budget line the moment both verticals coexist in one
        # database (this broke exactly that way; see the base model's
        # `_get_anchor_record` docstring, which already tolerates "no
        # anchor" as a normal case).
        string='Trade Budget',
        ondelete='cascade',
        index=True
    )
    trade_id = fields.Many2one(
        'trading.trade',
        string='Trade',
        related='trade_budget_id.trade_id',
        store=True,
        index=True
    )

    pnl_contributed_amount = fields.Float(default=0.0)
    pnl_contributed_field = fields.Char(default=False)

    # === ANCHOR PROVIDER REGISTRATION ===
    # Registered via _anchor_providers() rather than overriding
    # _get_anchor_record()/etc. directly, since omni_budget also extends
    # operations.budget.line with its own anchor -- see
    # operations_budget_line.py's (shared/budgets) docstring for why bare
    # hook-method overrides would collide between the two.

    def _anchor_providers(self):
        return super()._anchor_providers() + [{
            'owns_line': lambda: bool(self.trade_budget_id),
            'anchor_record': self._trading_anchor_record,
            'anchor_link_vals': self._trading_anchor_link_vals,
            'display_name_prefix': self._trading_anchor_display_name_prefix,
            'notify_amount_change': self._trading_anchor_notify_amount_change,
            'conversion_company': self._trading_anchor_conversion_company,
            'target_currency': self._trading_anchor_target_currency,
        }]

    def _trading_anchor_record(self):
        return self.trade_budget_id

    def _trading_anchor_link_vals(self):
        if not self.trade_id:
            return {}
        return {'trade_id': self.trade_id.id}

    def _trading_anchor_display_name_prefix(self):
        return self.trade_id.name or ''

    def _trading_anchor_conversion_company(self):
        return self.trade_id.company_id or self.env.company

    def _trading_anchor_target_currency(self):
        return self.trade_id.currency_id or self.currency_id

    def _trading_anchor_notify_amount_change(self):
        self._sync_pnl_contribution()

    def _get_pnl_target(self):
        self.ensure_one()
        if not self.trade_id or self.account_move_id:
            return None
        if self.line_type == 'expense':
            return ('additional_costs', self.actual_amount)
        if self.line_type == 'other':
            return ('additional_costs', -self.actual_amount)
        if self.line_type == 'charge':
            return ('additional_revenue', self.actual_amount)
        return None

    def _sync_pnl_contribution(self):
        for line in self:
            if not isinstance(line.id, int):
                continue
            trade = line.trade_id
            if not trade:
                continue

            if line.pnl_contributed_amount and line.pnl_contributed_field:
                current = trade[line.pnl_contributed_field]
                trade.write({line.pnl_contributed_field: max(current - line.pnl_contributed_amount, 0.0)})

            target = line._get_pnl_target()
            bookkeeping_vals = {'pnl_contributed_amount': 0.0, 'pnl_contributed_field': False}
            if target:
                field_name, amount = target
                current = trade[field_name]
                trade.write({field_name: current + amount})
                bookkeeping_vals = {'pnl_contributed_amount': amount, 'pnl_contributed_field': field_name}

            if (line.pnl_contributed_amount, line.pnl_contributed_field) != (
                bookkeeping_vals['pnl_contributed_amount'], bookkeeping_vals['pnl_contributed_field']
            ):
                line.sudo().with_context(skip_expense_update=True).write(bookkeeping_vals)

            trade._compute_all_trade_fields()

    def unlink(self):
        for line in self:
            trade = line.trade_id
            if trade and line.pnl_contributed_amount and line.pnl_contributed_field:
                current = trade[line.pnl_contributed_field]
                trade.write({line.pnl_contributed_field: max(current - line.pnl_contributed_amount, 0.0)})
                trade._compute_all_trade_fields()
        return super().unlink()