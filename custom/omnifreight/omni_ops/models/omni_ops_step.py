# -*- coding: utf-8 -*-
from odoo import fields, models


class OmniOpsStep(models.Model):
    """Operational step in the process. Each step has a sequence, a service
    type (FOB, Freight, Destination) and is linked to a freight file
    (omni.ops.file)"""
    _name = 'omni.ops.step'
    _description = 'Freight Operational Step'
    _inherit = ['process.step.mixin']
    _order = 'sequence, id'

    name = fields.Char(required=True)
    file_id = fields.Many2one(
        'omni.ops.file', string='Freight File', required=True,
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
