# -*- coding: utf-8 -*-
from unittest.mock import patch

from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestHrExpenseAnchorProviders(TransactionCase):
    """Exercises hr.expense's _budget_anchor_providers()/_onchange_budget_line_id_anchor()
    registry directly, with two synthetic providers standing in for two real
    industry modules (omni_budget's file_id, ele_trading_budget's trade_id)
    -- proving each provider's own field only ever gets set from a budget
    line that provider itself claims, rather than relying on the two real
    industries happening to pick non-colliding field names today."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Expense = cls.env['hr.expense']
        cls.Line = cls.env['operations.budget.line']

    def _provider(self, field, value):
        return {'field': field, 'get_from_budget_line': lambda line: value}

    def test_default_providers_is_empty(self):
        expense = self.Expense.new({})
        self.assertEqual(expense._budget_anchor_providers(), [])

    def test_onchange_sets_only_the_field_its_own_provider_targets(self):
        """Two providers registered, targeting two different (dummy, but
        real) hr.expense fields -- both should be applied, each writing only
        its own field, neither clobbering the other."""
        line = self.Line.create({'name': 'Test line', 'line_type': 'expense'})
        expense = self.Expense.new({'ele_budget_line_id': line.id})

        providers = [
            self._provider('employee_id', self.env.user.employee_id),
            self._provider('payment_mode', 'company_account'),
        ]
        with patch.object(type(expense), '_budget_anchor_providers', return_value=providers):
            expense._onchange_budget_line_id_anchor()

        self.assertEqual(expense.payment_mode, 'company_account')

    def test_onchange_is_a_noop_when_no_budget_line_selected(self):
        expense = self.Expense.new({})
        default_payment_mode = expense.payment_mode  # 'own_account' by default, not empty
        providers = [self._provider('payment_mode', 'company_account')]
        with patch.object(type(expense), '_budget_anchor_providers', return_value=providers):
            expense._onchange_budget_line_id_anchor()  # must not raise, must not apply any provider
        self.assertEqual(expense.payment_mode, default_payment_mode)

    def test_falsy_provider_value_leaves_the_field_untouched(self):
        """A provider whose getter returns False/empty for this particular
        budget line (e.g. omni_budget's provider when the line has no
        mrp_budget_id at all) must not overwrite the field with a falsy
        value -- only a real anchor should ever be written."""
        line = self.Line.create({'name': 'Test line', 'line_type': 'expense'})
        expense = self.Expense.new({'ele_budget_line_id': line.id, 'payment_mode': 'own_account'})

        providers = [self._provider('payment_mode', False)]
        with patch.object(type(expense), '_budget_anchor_providers', return_value=providers):
            expense._onchange_budget_line_id_anchor()

        self.assertEqual(expense.payment_mode, 'own_account')
