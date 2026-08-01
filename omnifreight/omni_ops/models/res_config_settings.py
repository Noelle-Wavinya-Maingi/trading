# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    """Settings UI for the per-company freight operations configuration defined
    on res.company. All fields are plain related fields so the company record
    stays the single source of truth."""
    _inherit = 'res.config.settings'

    omni_service_category_id = fields.Many2one(
        related='company_id.omni_service_category_id', readonly=False,
    )
    omni_tolerance_account_ids = fields.Many2many(
        related='company_id.omni_tolerance_account_ids', readonly=False,
    )
    omni_bank_charge_patterns = fields.Text(
        related='company_id.omni_bank_charge_patterns', readonly=False,
    )
    omni_internal_transfer_keywords = fields.Text(
        related='company_id.omni_internal_transfer_keywords', readonly=False,
    )
    omni_fob_workcenter_id = fields.Many2one(
        related='company_id.omni_fob_workcenter_id', readonly=False,
    )
    omni_freight_workcenter_id = fields.Many2one(
        related='company_id.omni_freight_workcenter_id', readonly=False,
    )
    omni_lod_workcenter_id = fields.Many2one(
        related='company_id.omni_lod_workcenter_id', readonly=False,
    )
    omni_bill_approver_group_id = fields.Many2one(
        related='company_id.omni_bill_approver_group_id', readonly=False,
    )
