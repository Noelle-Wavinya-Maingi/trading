# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged

from ..models.res_company import (
    DEFAULT_BANK_CHARGE_PATTERNS,
    DEFAULT_INTERNAL_TRANSFER_KEYWORDS,
    DEFAULT_TOLERANCE_ACCOUNT_CODES,
)


@tagged('post_install', '-at_install')
class TestBankReconcileConfig(TransactionCase):
    """The account codes, fee patterns and transfer keywords used to classify a
    statement line were hardcoded (and Belgian/English-specific). They are now
    per-company settings. Each resolver must return the historical literal when
    unset, and the configured value once set."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company

    def test_tolerance_codes_fall_back_to_historical_literals(self):
        self.company.ele_tolerance_account_ids = False
        self.assertEqual(
            self.company._ele_get_tolerance_account_codes(),
            DEFAULT_TOLERANCE_ACCOUNT_CODES,
        )

    def test_tolerance_codes_use_configured_accounts(self):
        account = self.env['account.account'].create({
            'name': 'Custom Tolerance',
            'code': '999123',
            'account_type': 'expense',
        })
        self.company.ele_tolerance_account_ids = [(6, 0, account.ids)]
        self.assertEqual(self.company._ele_get_tolerance_account_codes(), ['999123'])

    def test_bank_charge_patterns_fall_back_when_blank(self):
        self.company.ele_bank_charge_patterns = False
        self.assertEqual(
            self.company._ele_get_bank_charge_patterns(),
            DEFAULT_BANK_CHARGE_PATTERNS,
        )

    def test_bank_charge_patterns_parse_lines_and_ignore_blanks(self):
        self.company.ele_bank_charge_patterns = "frais\n\n  commission  \n"
        self.assertEqual(
            self.company._ele_get_bank_charge_patterns(),
            ['frais', 'commission'],
        )

    def test_transfer_keywords_fall_back_when_blank(self):
        self.company.ele_internal_transfer_keywords = ''
        self.assertEqual(
            self.company._ele_get_internal_transfer_keywords(),
            DEFAULT_INTERNAL_TRANSFER_KEYWORDS,
        )

    def test_transfer_keywords_are_lowercased(self):
        self.company.ele_internal_transfer_keywords = "Virement Interne\nOVERBOEKING"
        self.assertEqual(
            self.company._ele_get_internal_transfer_keywords(),
            ['virement interne', 'overboeking'],
        )

    def test_tolerance_account_detection_uses_configured_codes(self):
        """End-to-end through the statement line, not just the resolver."""
        account = self.env['account.account'].create({
            'name': 'Rounding', 'code': '998877', 'account_type': 'expense',
        })
        self.company.ele_tolerance_account_ids = [(6, 0, account.ids)]
        line = self.env['account.bank.statement.line']
        self.assertTrue(line._is_tolerance_account('998877'))
        self.assertFalse(line._is_tolerance_account('655000'))
