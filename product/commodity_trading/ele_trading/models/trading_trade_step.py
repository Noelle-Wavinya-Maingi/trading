# -*- coding: utf-8 -*-
from odoo import fields, models


class TradingTradeStep(models.Model):
    """Trading's own concrete operational step model. Exists only to prove
    process.step.mixin's shape works for a real vertical -- nothing in
    Trading creates a step today (commodity trading has no post-confirm
    operational process to track; its draft/confirmed/closed lifecycle,
    trading_trade.py's `status`, already covers what Trading needs). See
    docs/PROCESS_ENGINE_MIGRATION_PLAN.md Phase 0."""
    _name = 'trading.trade.step'
    _description = 'Trading Trade Step'
    _inherit = ['process.step.mixin']
    _order = 'sequence, id'

    name = fields.Char(required=True)
    ele_trade_id = fields.Many2one('trading.trade', string='Trade', required=True, ondelete='cascade', index=True)
    blocked_by_step_ids = fields.Many2many(
        'trading.trade.step',
        'trading_trade_step_blocked_by_rel',
        'step_id',
        'blocked_by_id',
        string='Blocked By',
    )
