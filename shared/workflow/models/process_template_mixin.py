# -*- coding: utf-8 -*-
from odoo import fields, models


class ProcessTemplateMixin(models.AbstractModel):
    """Mixin for models that are process templates"""
    _name = 'workflow.template.mixin'
    _description = 'Process Template Mixin'

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    def _template_step_model(self):
        """Technical name of the concrete step model this template
        generates records in. Override in the including model."""
        raise NotImplementedError

    def _template_step_vals(self, anchor, template_step):
        """Return a dict of values to create a concrete step record on `anchor`"""
        raise NotImplementedError

    def generate_steps(self, anchor):
        """Generate concrete step records on `anchor` from this template's steps."""
        self.ensure_one()
        Step = self.env[self._template_step_model()]
        vals_list = [
            self._template_step_vals(anchor, template_step)
            for template_step in self.template_step_ids.sorted('sequence')
        ]
        return Step.create(vals_list) if vals_list else Step
