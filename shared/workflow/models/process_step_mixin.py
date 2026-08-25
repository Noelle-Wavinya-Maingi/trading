# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ProcessStepMixin(models.AbstractModel):
    """A single operational step, inherited by a vertical's own concrete
    step model (its comodel is vertical-specific, exactly like
    budget.document.mixin is inherited by each vertical's own budget
    header model -- there is no single shared step table across verticals).

    Deliberately not mrp.workorder-shaped: no quality checks, no
    work-center/resource assignment, no calendar-based duration. Freight
    operations are outsourced to third-party suppliers, so there's no
    internal resource to schedule and no reliable basis to estimate
    duration against -- a plain draft -> in_progress -> done status is the
    actual need, not a scheduling engine.

    `blocked_by_step_ids` (dependency between steps) is deliberately NOT
    declared here: its comodel is the including model's own concrete step
    model, which the mixin has no way to name generically. Each vertical
    that wants sequencing defines its own `blocked_by_step_ids` Many2many
    pointing at itself -- sequencing is optional, so a vertical with no
    need for it simply never adds the field."""
    _name = 'workflow.step.mixin'
    _description = 'Process Step Mixin'

    sequence = fields.Integer('Sequence', default=10)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('done', 'Done'),
    ], string='Status', default='draft', required=True)

    def action_start(self):
        self.write({'state': 'in_progress'})

    def action_done(self):
        self.write({'state': 'done'})
