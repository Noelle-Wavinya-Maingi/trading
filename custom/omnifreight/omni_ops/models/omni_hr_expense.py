# -*- coding: utf-8 -*-
from odoo import fields, models


class OmniHrExpense(models.Model):
    """Link an expense to the freight manufacturing order (file) it belongs to.

    Budget linkage lives in omni_budget and bill matching in ele_ap_validation;
    this file deliberately keeps only the freight file reference so core freight
    operations need neither of those modules."""
    _inherit = 'hr.expense'

    production_id = fields.Many2one(
        'mrp.production',
        string='Manufacturing Order / File Number',
        help='Manufacturing order (file number) this expense is related to',
        tracking=True,
        index=True,
    )
    file_number = fields.Char(
        string='File Number',
        related='production_id.name',
        store=True,
        readonly=True,
        help='File number from the manufacturing order',
    )
