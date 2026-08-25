# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class TradingTradeBudgetBridge(models.Model):
    """Adds the optional Trade Budget feature onto trading.trade. Lives in
    the 'ele_trading_budget' bridge module (depends on both 'ele_trading' and
    'budgets') so that installing/uninstalling this feature never touches
    core Trading."""
    _name = 'trading.trade'
    _inherit = ['trading.trade', 'budget.flag.mixin']

    budget_ids = fields.One2many('trading.trade.budget', 'ele_trade_id', string='Budgets')
    budget_id = fields.Many2one(
        'trading.trade.budget',
        string='Budget',
        compute='_compute_budget_id',
        store=True
    )

    # Fulfills the contract trading_trade.py's own ele_has_budget stub
    # promises: this module overrides it into a real compute. Without this,
    # ele_has_budget stays permanently False and every view gated on it
    # (this module's own budget tab, plus ele_trading's fallback cards)
    # never reflects a real budget being created.
    ele_has_budget = fields.Boolean(compute='_compute_ele_has_budget', store=True)

    @api.depends('budget_ids')
    def _compute_budget_id(self):
        for record in self:
            record.budget_id = record.budget_ids[:1].id if record.budget_ids else False

    @api.depends('has_budget')
    def _compute_ele_has_budget(self):
        for record in self:
            record.ele_has_budget = record.has_budget

    def action_create_budget(self):
        """Create the (single) budget for this trade."""
        self.ensure_one()
        if self.budget_ids:
            raise ValidationError(_("This trade already has a budget."))

        budget = self.env['trading.trade.budget'].create({
            'ele_trade_id': self.id,
            'currency_id': self.currency_id.id,
        })
        return self._bridge_open_budget_action(budget)

    def action_view_budget(self):
        """View this trade's budget."""
        return self._bridge_open_budget_action(self.budget_id)

    def _sync_budget_line_for_move(self, move, field_name, amount):
        """Sync the budget line for a given account move. This is called when an account move is created or updated, and it ensures that the corresponding budget line is created or updated accordingly.
        """
        self.ensure_one()
        if not self.budget_id:
            return

        BudgetLine = self.env['operations.budget.line']
        existing = BudgetLine.search([
            ('ele_trade_budget_id', '=', self.budget_id.id),
            ('account_move_id', '=', move.id),
        ], limit=1)

        line_type = 'charge' if field_name == 'ele_additional_revenue' else 'expense'

        vals = {
            'name': move.name or move.ref or 'Invoice/Bill',
            'line_type': line_type,
            'actual_amount': abs(amount),
            'account_move_id': move.id,
            'partner_id': move.partner_id.id if move.partner_id else False,
            'date_actual': move.invoice_date or move.date,
        }

        if existing:
            existing.write(vals)
        else:
            vals['ele_trade_budget_id'] = self.budget_id.id
            BudgetLine.create(vals)

    def _remove_budget_line_for_move(self, move):
        self.ensure_one()

        if not self.budget_id:
            return

        self.env['operations.budget.line'].search([
            ('ele_trade_budget_id', '=', self.budget_id.id),
            ('account_move_id', '=', move.id)
        ]).unlink()