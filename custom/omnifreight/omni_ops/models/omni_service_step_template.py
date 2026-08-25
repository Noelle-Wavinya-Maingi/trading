# -*- coding: utf-8 -*-
from odoo import fields, models


class OmniServiceStepTemplate(models.Model):
    """Template for a freight service step. Each template can have multiple steps,
    which are used to generate the actual operational steps for a given freight file
    (omni.ops.file)."""
    _name = 'omni.service.step.template'
    _description = 'Freight Service Step Template'
    _inherit = ['workflow.template.mixin']
    _order = 'sequence, id'

    sequence = fields.Integer(default=100)
    service_scope = fields.Selection([
        ('fob', 'FOB'),
        ('freight', 'Freight'),
        ('lod', 'Destination'),
        ('fob_freight', 'FOB + Freight'),
        ('freight_lod', 'Freight + Destination'),
        ('fob_lod', 'FOB + Destination'),
        ('fob_freight_lod', 'FOB + Freight + Destination'),
    ], string='Service Scope', required=True)
    template_step_ids = fields.One2many(
        'omni.service.step.template.line', 'template_id', string='Steps', copy=True
    )

    def _template_step_model(self):
        return 'omni.ops.step'

    def _template_step_vals(self, anchor, template_step):
        return {
            'name': template_step.name,
            'sequence': template_step.sequence,
            'file_id': anchor.id,
            'service_type': template_step.service_type,
        }


class OmniServiceStepTemplateLine(models.Model):
    """A single step in a freight service step template. Each line has a sequence and a service type (FOB, Freight, Destination)."""
    _name = 'omni.service.step.template.line'
    _description = 'Freight Service Step Template Line'
    _inherit = ['workflow.template.step.mixin']
    _order = 'sequence, id'

    template_id = fields.Many2one(
        'omni.service.step.template', string='Template', required=True,
        ondelete='cascade', index=True,
    )
    service_type = fields.Selection([
        ('fob', 'FOB Operations'),
        ('freight', 'Freight Operations'),
        ('lod', 'Destination Operations'),
    ], string='Service Type', required=True)
