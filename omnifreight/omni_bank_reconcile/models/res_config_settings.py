# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    """Settings UI for bank reconciliation matching. Plain related fields, so the
    company record stays the single source of truth."""
    _inherit = 'res.config.settings'

    omni_tolerance_account_ids = fields.Many2many(
        related='company_id.omni_tolerance_account_ids', readonly=False,
    )
    omni_bank_charge_patterns = fields.Text(
        related='company_id.omni_bank_charge_patterns', readonly=False,
    )
    omni_internal_transfer_keywords = fields.Text(
        related='company_id.omni_internal_transfer_keywords', readonly=False,
    )
