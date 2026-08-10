# -*- coding: utf-8 -*-
from odoo import fields, models


class OmniOpsStep(models.Model):
    """Operational step in the process. Each step is has a sequence has a service type (FOB, Freight, Destination) and is linked to a manufacturing order."""
    _name = 'omni.ops.step'
    _description = 'Freight Operational Step'
    _inherit = ['process.step.mixin']
    _order = 'sequence, id'

    name = fields.Char(required=True)
    production_id = fields.Many2one(
        'mrp.production', string='Manufacturing Order', required=True,
        ondelete='cascade', index=True,
    )
    service_type = fields.Selection([
        ('fob', 'FOB Operations'),
        ('freight', 'Freight Operations'),
        ('lod', 'Destination Operations'),
    ], string='Service Type', required=True)
    blocked_by_step_ids = fields.Many2many(
        'omni.ops.step',
        'omni_ops_step_blocked_by_rel',
        'step_id',
        'blocked_by_id',
        string='Blocked By',
    )
