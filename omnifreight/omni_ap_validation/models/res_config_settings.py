# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    omni_bill_approver_group_id = fields.Many2one(
        related='company_id.omni_bill_approver_group_id', readonly=False,
    )
