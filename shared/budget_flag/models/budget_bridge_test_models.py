# -*- coding: utf-8 -*-
from odoo import api, fields, models


class BudgetBridgeTestDocument(models.Model):
    """Test-only budget header, playing the role trading.trade.budget /
    a freight budget play for budget.document.mixin. Lives in models/,
    not tests/, for the same reason as
    shared/dispatch/models/order_bridge_test_host.py."""
    _name = 'budget.bridge.test.document'
    _description = 'Budget Bridge Test Document'
    _inherit = ['budget.document.mixin']

    host_id = fields.Many2one('budget.bridge.test.host', ondelete='cascade')

    def _budget_sequence_code(self):
        return 'budget.bridge.test.document'


class BudgetBridgeTestHost(models.Model):
    """Test-only stand-in for an anchor model (trading.trade, a freight
    file). Every real budget.bridge.mixin including model defines its own
    budget_id (singular, the 'active' budget among budget_ids) -- the
    mixin's _compute_budget_state depends on it but can't define it itself,
    since its comodel is vertical-specific."""
    _name = 'budget.bridge.test.host'
    _description = 'Budget Bridge Test Host'
    _inherit = ['budget.bridge.mixin']

    name = fields.Char(default='Test Host')
    budget_ids = fields.One2many('budget.bridge.test.document', 'host_id')
    budget_id = fields.Many2one(
        'budget.bridge.test.document',
        compute='_compute_budget_id',
        store=True,
    )

    @api.depends('budget_ids')
    def _compute_budget_id(self):
        for host in self:
            host.budget_id = host.budget_ids[:1]
