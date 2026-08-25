# -*- coding: utf-8 -*-
from odoo import fields, models


class ProcessTemplateStepMixin(models.AbstractModel):
    """Mixin for models that are process template steps"""
    _name = 'workflow.template.step.mixin'
    _description = 'Process Template Step Mixin'

    name = fields.Char(required=True)
    sequence = fields.Integer('Sequence', default=10)
