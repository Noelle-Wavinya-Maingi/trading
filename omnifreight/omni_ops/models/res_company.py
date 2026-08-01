# -*- coding: utf-8 -*-
from odoo import fields, models

# Fallback defaults, used only when a company has not configured its own values.
# These reproduce the literals that were previously hardcoded throughout this
# module, so an existing install behaves identically until it is configured.
DEFAULT_SERVICE_CATEGORY_NAME = 'Omnifreight Services'
DEFAULT_TOLERANCE_ACCOUNT_CODES = ['655000', '755000']
DEFAULT_BANK_CHARGE_PATTERNS = [
    r'bank\s*charge',
    r'bank\s*fee',
    r'service\s*charge',
    r'maintenance\s*fee',
    r'monthly\s*fee',
    r'transaction\s*fee',
    r'wire\s*fee',
    r'transfer\s*fee',
    r'atm\s*fee',
    r'overdraft\s*fee',
    r'late\s*fee',
    r'interest\s*charge',
    r'processing\s*fee',
    r'foreign\s*transaction',
    r'international\s*fee',
]
DEFAULT_INTERNAL_TRANSFER_KEYWORDS = [
    'money movement',
    'internal transfer',
    'fund transfer',
    'capital gain',
    'forex',
    'exchange',
]


class ResCompany(models.Model):
    """Per-company configuration for freight operations.

    Everything here was previously a literal buried in this module's Python --
    a product category matched by name, a pair of Belgian GL account codes, a
    set of English keyword patterns, workcenters resolved by fuzzy name match,
    and a hardcoded approver group. None of those hold for a second freight
    client, so each is now configurable, with the original literal kept as the
    fallback default so existing installs are unaffected."""
    _inherit = 'res.company'

    omni_service_category_id = fields.Many2one(
        'product.category',
        string='Freight Service Product Category',
        help="Category assigned to freight service products. If unset, falls back "
             "to a category named '%s'." % DEFAULT_SERVICE_CATEGORY_NAME,
    )
    omni_tolerance_account_ids = fields.Many2many(
        'account.account',
        'omni_company_tolerance_account_rel',
        'company_id',
        'account_id',
        string='Reconciliation Tolerance Accounts',
        help="Accounts that represent small write-off/tolerance differences during "
             "bank reconciliation. Chart-of-accounts specific. If unset, falls back "
             "to codes %s." % ', '.join(DEFAULT_TOLERANCE_ACCOUNT_CODES),
    )
    omni_bank_charge_patterns = fields.Text(
        string='Bank Charge Patterns',
        help="One regular expression per line, matched case-insensitively against "
             "account names and transaction labels to identify bank fees. If blank, "
             "a built-in English default list is used.",
    )
    omni_internal_transfer_keywords = fields.Text(
        string='Internal Transfer Keywords',
        help="One keyword per line. An account name containing any of these marks the "
             "transaction as an internal transfer or forex movement rather than a "
             "missing invoice. If blank, a built-in English default list is used.",
    )
    omni_fob_workcenter_id = fields.Many2one(
        'mrp.workcenter', string='FOB Workcenter',
        help="Workcenter used for FOB service operations.",
    )
    omni_freight_workcenter_id = fields.Many2one(
        'mrp.workcenter', string='Freight Workcenter',
        help="Workcenter used for Freight service operations.",
    )
    omni_lod_workcenter_id = fields.Many2one(
        'mrp.workcenter', string='Destination (LOD) Workcenter',
        help="Workcenter used for Destination/LOD service operations.",
    )
    omni_bill_approver_group_id = fields.Many2one(
        'res.groups',
        string='Bill Validation Approver Group',
        help="Group whose members can validate vendor bills. If unset, falls back to "
             "Administration / Settings (base.group_erp_manager).",
    )

    # === RESOLVERS (configured value first, historical literal as fallback) ===
    def _omni_get_service_category(self):
        """Product category for freight service products."""
        self.ensure_one()
        if self.omni_service_category_id:
            return self.omni_service_category_id
        return self.env['product.category'].search(
            [('name', '=', DEFAULT_SERVICE_CATEGORY_NAME)], limit=1
        )

    def _omni_get_tolerance_account_codes(self):
        """Account codes treated as reconciliation tolerance."""
        self.ensure_one()
        if self.omni_tolerance_account_ids:
            return self.omni_tolerance_account_ids.mapped('code')
        return list(DEFAULT_TOLERANCE_ACCOUNT_CODES)

    def _omni_get_bank_charge_patterns(self):
        """Regexes identifying bank fees."""
        self.ensure_one()
        return self._omni_split_lines(self.omni_bank_charge_patterns) or list(DEFAULT_BANK_CHARGE_PATTERNS)

    def _omni_get_internal_transfer_keywords(self):
        """Lower-cased keywords identifying internal transfers / forex movements."""
        self.ensure_one()
        configured = self._omni_split_lines(self.omni_internal_transfer_keywords)
        return [kw.lower() for kw in configured] or list(DEFAULT_INTERNAL_TRANSFER_KEYWORDS)

    @staticmethod
    def _omni_split_lines(value):
        """Split a Text config field into a clean list, ignoring blanks."""
        if not value:
            return []
        return [line.strip() for line in value.splitlines() if line.strip()]

    def _omni_get_workcenter(self, service_type):
        """Resolve the workcenter backing a service type.

        Prefers the explicitly configured workcenter. Falls back to the previous
        behaviour -- a fuzzy name match, then creating one -- so nothing breaks on
        an unconfigured install. Note the fallback's `ilike` is deliberately
        imprecise and can match an unrelated workcenter; configuring the fields
        above is what makes this deterministic."""
        self.ensure_one()
        if not service_type:
            return self.env['mrp.workcenter']

        configured = {
            'fob': self.omni_fob_workcenter_id,
            'freight': self.omni_freight_workcenter_id,
            'lod': self.omni_lod_workcenter_id,
        }.get(service_type)
        if configured:
            return configured

        Workcenter = self.env['mrp.workcenter']
        workcenter = Workcenter.search([('name', 'ilike', service_type)], limit=1)
        if not workcenter:
            workcenter = Workcenter.create({
                'name': f'{service_type.upper()} Operations',
                'code': service_type.upper(),
            })
        return workcenter

    def _omni_get_bill_approver_group(self):
        """Group whose members may validate vendor bills."""
        self.ensure_one()
        return self.omni_bill_approver_group_id or self.env.ref(
            'base.group_erp_manager', raise_if_not_found=False
        )
