# -*- coding: utf-8 -*-
from odoo import fields, models

# Fallback defaults, used only when a company has not configured its own values.
# These reproduce the literals that were previously hardcoded in the statement
# matching code, so an existing install behaves identically until configured.
# They are English- and Belgian-CoA-flavoured, which is precisely why they are
# defaults rather than constants.
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
    """Per-company configuration for bank statement match classification."""
    _inherit = 'res.company'

    ele_tolerance_account_ids = fields.Many2many(
        'account.account',
        'ele_company_tolerance_account_rel',
        'company_id',
        'account_id',
        string='Reconciliation Tolerance Accounts',
        help="Accounts that represent small write-off/tolerance differences during "
             "bank reconciliation. Chart-of-accounts specific. If unset, falls back "
             "to codes %s." % ', '.join(DEFAULT_TOLERANCE_ACCOUNT_CODES),
    )
    ele_bank_charge_patterns = fields.Text(
        string='Bank Charge Patterns',
        help="One regular expression per line, matched case-insensitively against "
             "account names and transaction labels to identify bank fees. If blank, "
             "a built-in English default list is used.",
    )
    ele_internal_transfer_keywords = fields.Text(
        string='Internal Transfer Keywords',
        help="One keyword per line. An account name containing any of these marks the "
             "transaction as an internal transfer or forex movement rather than a "
             "missing invoice. If blank, a built-in English default list is used.",
    )

    # === RESOLVERS (configured value first, historical literal as fallback) ===
    def _ele_get_tolerance_account_codes(self):
        """Account codes treated as reconciliation tolerance."""
        self.ensure_one()
        if self.ele_tolerance_account_ids:
            return self.ele_tolerance_account_ids.mapped('code')
        return list(DEFAULT_TOLERANCE_ACCOUNT_CODES)

    def _ele_get_bank_charge_patterns(self):
        """Regexes identifying bank fees."""
        self.ensure_one()
        return self._ele_split_lines(self.ele_bank_charge_patterns) or list(DEFAULT_BANK_CHARGE_PATTERNS)

    def _ele_get_internal_transfer_keywords(self):
        """Lower-cased keywords identifying internal transfers / forex movements."""
        self.ensure_one()
        configured = self._ele_split_lines(self.ele_internal_transfer_keywords)
        return [kw.lower() for kw in configured] or list(DEFAULT_INTERNAL_TRANSFER_KEYWORDS)

    @staticmethod
    def _ele_split_lines(value):
        """Split a Text config field into a clean list, ignoring blanks."""
        if not value:
            return []
        return [line.strip() for line in value.splitlines() if line.strip()]
