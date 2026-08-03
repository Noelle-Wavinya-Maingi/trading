# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    """Per-company configuration for the vendor bill approval workflow."""
    _inherit = 'res.company'

    omni_bill_approver_group_id = fields.Many2one(
        'res.groups',
        string='Bill Validation Approver Group',
        help="Group whose members can validate vendor bills. If unset, falls back to "
             "Administration / Settings (base.group_erp_manager).",
    )

    def _omni_get_bill_approver_group(self):
        """Group whose members may validate vendor bills."""
        self.ensure_one()
        return self.omni_bill_approver_group_id or self.env.ref(
            'base.group_erp_manager', raise_if_not_found=False
        )
