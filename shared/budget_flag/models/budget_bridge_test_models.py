# -*- coding: utf-8 -*-
from odoo import api, fields, models


class BudgetFlagTestDocument(models.Model):
    """Test-only budget header, playing the role trading.trade.budget /
    a freight budget play for budget.document.mixin. Lives in models/,
    not tests/, for the same reason as
    shared/dispatch/models/order_bridge_test_host.py."""
    _name = 'budget.flag.test.document'
    _description = 'Budget Flag Test Document'
    _inherit = ['budget.document.mixin']

    host_id = fields.Many2one('budget.flag.test.host', ondelete='cascade')

    def _budget_sequence_code(self):
        return 'budget.flag.test.document'


class BudgetFlagTestHost(models.Model):
    """Test-only stand-in for an anchor model (trading.trade, a freight
    file). Every real budget.flag.mixin including model defines its own
    budget_id (singular, the 'active' budget among budget_ids) -- the
    mixin's _compute_budget_state depends on it but can't define it itself,
    since its comodel is vertical-specific."""
    _name = 'budget.flag.test.host'
    _description = 'Budget Flag Test Host'
    _inherit = ['budget.flag.mixin']

    name = fields.Char(default='Test Host')
    budget_ids = fields.One2many('budget.flag.test.document', 'host_id')
    budget_id = fields.Many2one(
        'budget.flag.test.document',
        compute='_compute_budget_id',
        store=True,
    )

    @api.depends('budget_ids')
    def _compute_budget_id(self):
        for host in self:
            host.budget_id = host.budget_ids[:1]
