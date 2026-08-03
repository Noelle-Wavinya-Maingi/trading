# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    """Settings UI for bank reconciliation matching. Plain related fields, so the
    company record stays the single source of truth."""
    _inherit = 'res.config.settings'

    ele_tolerance_account_ids = fields.Many2many(
        related='company_id.ele_tolerance_account_ids', readonly=False,
    )
    ele_bank_charge_patterns = fields.Text(
        related='company_id.ele_bank_charge_patterns', readonly=False,
    )
    ele_internal_transfer_keywords = fields.Text(
        related='company_id.ele_internal_transfer_keywords', readonly=False,
    )
