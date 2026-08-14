# -*- coding: utf-8 -*-
from unittest.mock import patch

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestOperationsBudgetLine(TransactionCase):
    """Exercises the core operations.budget.line model standalone -- no client
    bridge module (trading_budget, omni_ops, ...) and no actualization backend
    (budgets_hr_expense) installed. Everything here must hold for `budgets` on
    its own, since that's the whole point of keeping it dependency-free."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Line = cls.env['operations.budget.line']

    def _create_line(self, **vals):
        vals.setdefault('name', 'Test line')
        vals.setdefault('line_type', 'expense')
        return self.Line.create(vals)

    # === display_type / constraints ===
    def test_section_row_is_valid_without_line_type(self):
        line = self.Line.create({'name': 'Header', 'display_type': 'line_section', 'line_type': False})
        self.assertEqual(line.display_type, 'line_section')

    def test_normal_line_requires_line_type(self):
        with self.assertRaises(ValidationError):
            self.Line.create({'name': 'x', 'line_type': False})

    def test_section_cannot_have_line_type(self):
        with self.assertRaises(ValidationError):
            self.Line.create({'name': 'x', 'display_type': 'line_section', 'line_type': 'expense'})

    def test_negative_budgeted_amount_rejected(self):
        with self.assertRaises(ValidationError):
            self._create_line(budgeted_amount=-10.0)

    def test_negative_actual_amount_rejected(self):
        with self.assertRaises(ValidationError):
            self._create_line(actual_amount=-10.0)

    def test_section_cannot_link_account_move(self):
        vendor = self.env['res.partner'].create({'name': 'Test Vendor'})
        move = self.env['account.move'].create({'move_type': 'in_invoice', 'partner_id': vendor.id})
        with self.assertRaises(ValidationError):
            self.Line.create({
                'name': 'x', 'display_type': 'line_section', 'line_type': False,
                'account_move_id': move.id,
            })

    # === computed fields ===
    def test_variance_is_actual_minus_budgeted(self):
        line = self._create_line(budgeted_amount=100.0, actual_amount=80.0)
        self.assertEqual(line.variance_amount, -20.0)

    def test_amount_company_currency_passthrough_when_same_currency(self):
        line = self._create_line(actual_amount=50.0, currency_id=self.env.company.currency_id.id)
        self.assertEqual(line.amount_company_currency, 50.0)

    def test_source_reference_reflects_linked_invoice(self):
        vendor = self.env['res.partner'].create({'name': 'Test Vendor'})
        move = self.env['account.move'].create({'move_type': 'in_invoice', 'partner_id': vendor.id})
        line = self._create_line(account_move_id=move.id)
        self.assertEqual(line.source_reference, move)

    def test_source_reference_empty_with_no_document(self):
        line = self._create_line(actual_amount=10.0)
        self.assertFalse(line.source_reference)

    # === default hooks are no-ops without any bridge/backend module ===
    def test_default_anchor_is_empty(self):
        line = self._create_line(actual_amount=10.0)
        self.assertFalse(line._get_anchor_record())

    def test_default_anchor_link_vals_is_empty_dict(self):
        line = self._create_line(actual_amount=10.0)
        self.assertEqual(line._get_anchor_link_vals(), {})

    def test_default_notify_anchor_is_noop(self):
        line = self._create_line(actual_amount=10.0)
        line._notify_anchor_of_amount_change()  # must not raise

    def test_default_sync_actual_source_is_noop(self):
        """With no actualization backend installed, changing actual_amount never
        creates any backing document -- the line just trusts the value as entered."""
        line = self._create_line(actual_amount=10.0)
        line.write({'actual_amount': 25.0})  # must not raise, nothing else to assert on

    # === anchor chatter contract (_check_anchor_supports_chatter) ===
    def test_tracking_message_posted_when_anchor_supports_chatter(self):
        partner = self.env.user.partner_id
        with patch.object(type(self.Line), '_get_anchor_record', return_value=partner):
            line = self._create_line(name='Original name', actual_amount=10.0)
            count_before = len(partner.message_ids)
            line.write({'name': 'Changed name'})
        self.assertGreater(len(partner.message_ids), count_before)

    def test_write_blocked_when_anchor_lacks_chatter(self):
        """A client overriding _get_anchor_record() to return a non-mail.thread
        record gets a clear ValidationError, not an opaque AttributeError from
        deep inside message_post()."""
        non_chatter_anchor = self.env['res.currency'].browse(self.env.company.currency_id.id)
        with patch.object(type(self.Line), '_get_anchor_record', return_value=non_chatter_anchor):
            line = self._create_line(name='Original name', actual_amount=10.0)
            with self.assertRaises(ValidationError):
                line.write({'name': 'Changed name'})

    # === anchor provider registry (_anchor_providers/_active_anchor_provider) ===
    # These tests exercise the registry mechanism itself with two synthetic
    # providers, standing in for two real industries (omni_budget,
    # ele_trading_budget) -- proving the dispatch is correct on its own
    # merits, not just because the two real industries happen to both behave
    # today. This is the exact mechanism that silently broke once already:
    # a test that only ever registers zero or one provider can't catch a
    # regression in how *multiple* registered providers are told apart.

    def _make_provider(self, label, owns):
        """A minimal but complete provider dict -- every key
        _active_anchor_provider()'s callers can dereference, tagged with
        `label` so assertions can tell which provider actually ran."""
        return {
            'owns_line': lambda: owns,
            'anchor_record': lambda: self.env.user.partner_id,
            'anchor_link_vals': lambda: {'x_label': label},
            'display_name_prefix': lambda: label,
            'notify_amount_change': lambda: None,
            'conversion_company': lambda: self.env.company,
            'target_currency': lambda: self.env.company.currency_id,
        }

    def test_active_provider_is_the_one_that_owns_the_line(self):
        """With two providers registered and only the second claiming
        ownership, dispatch must pick the second one, not silently default
        to the first registered or the last registered."""
        line = self._create_line(actual_amount=10.0)
        providers = [self._make_provider('first', owns=False), self._make_provider('second', owns=True)]
        with patch.object(type(self.Line), '_anchor_providers', return_value=providers):
            self.assertEqual(line._get_display_name_prefix(), 'second')

    def test_first_registered_provider_wins_when_both_own_the_line(self):
        """Only one provider should ever legitimately claim a given line in
        practice (each industry's anchor field is mutually exclusive), but
        dispatch must still be deterministic -- first registered, first
        served -- rather than silently picking whichever happened to be
        installed last."""
        line = self._create_line(actual_amount=10.0)
        providers = [self._make_provider('first', owns=True), self._make_provider('second', owns=True)]
        with patch.object(type(self.Line), '_anchor_providers', return_value=providers):
            self.assertEqual(line._get_display_name_prefix(), 'first')

    def test_no_owning_provider_falls_back_to_the_base_default(self):
        """A line whose anchor field doesn't match ANY registered provider
        (e.g. a bare line with no industry bridge installed at all) must
        still behave like the zero-provider case, not raise or silently
        pick a provider that doesn't actually own it."""
        line = self._create_line(actual_amount=10.0)
        providers = [self._make_provider('first', owns=False), self._make_provider('second', owns=False)]
        with patch.object(type(self.Line), '_anchor_providers', return_value=providers):
            self.assertFalse(line._get_anchor_record())
            self.assertEqual(line._get_anchor_link_vals(), {})
            self.assertEqual(line._get_display_name_prefix(), '')
