# -*- coding: utf-8 -*-
from odoo import fields, models


class OmniHrExpense(models.Model):
    """Link an expense to the freight file it belongs to.

    Budget linkage lives in omni_budget and bill matching in ele_ap_validation;
    this file deliberately keeps only the freight file reference so core freight
    operations need neither of those modules."""
    _inherit = 'hr.expense'

    file_id = fields.Many2one(
        'omni.ops.file',
        string='Freight File',
        help='Freight file this expense is related to',
        tracking=True,
        index=True,
    )
    file_number = fields.Char(
        string='File Number',
        related='file_id.name',
        store=True,
        readonly=True,
        help='File number from the freight file',
    )
