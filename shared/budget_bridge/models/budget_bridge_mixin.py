# -*- coding: utf-8 -*-
from odoo import api, fields, models


class BudgetBridgeMixin(models.AbstractModel):
    """Lets an anchor model (trading.trade, mrp.production, ...) expose
    whether it has a budget without reimplementing the same Boolean/compute
    pair per vertical. The including model must define its own `budget_ids`
    One2many (the target model differs per vertical); this only supplies
    what's genuinely identical everywhere -- the derived flag."""
    _name = 'budget.bridge.mixin'
    _description = 'Budget Bridge Mixin'

    has_budget = fields.Boolean('Has Budget', compute='_compute_has_budget', store=True)

    @api.depends('budget_ids')
    def _compute_has_budget(self):
        for record in self:
            record.has_budget = bool(record.budget_ids)
