# -*- coding: utf-8 -*-
from odoo import api, fields, models


class WorkflowMixin(models.AbstractModel):
    """Lets an anchor model (trading.trade, a future freight-file model, ...)
    expose whether it has any operational steps, without depending on
    Odoo's `mrp` app. The including model must define its own `step_ids`
    One2many (the target model differs per vertical, exactly like
    budget.flag.mixin's `budget_ids`); this only supplies what's
    genuinely identical everywhere -- the derived flag.

    Zero steps is a fully supported case, not a placeholder: trading.trade
    adopts this mixin with no step model at all, to prove the shape isn't
    freight-specific before any real step-generation work is built."""
    _name = 'workflow.mixin'
    _description = 'Workflow Mixin'

    has_steps = fields.Boolean('Has Steps', compute='_compute_has_steps', store=True)

    @api.depends('step_ids')
    def _compute_has_steps(self):
        for record in self:
            record.has_steps = bool(record.step_ids)
