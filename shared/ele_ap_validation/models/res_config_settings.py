# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    ele_bill_approver_group_id = fields.Many2one(
        related='company_id.ele_bill_approver_group_id', readonly=False,
    )
