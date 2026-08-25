# -*- coding: utf-8 -*-
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestBudgetFlagMixin(TransactionCase):
    """Exercises has_budget/budget_state and _bridge_open_budget_action
    against budget.flag.test.host/.document (see
    shared/budget_flag/models/budget_bridge_test_models.py), and
    budget.document.mixin's own create/confirm/close logic -- none of
    budget_flag's actual logic had any test coverage before this."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Host = cls.env['budget.flag.test.host']
        cls.Document = cls.env['budget.flag.test.document']

    def test_has_budget_false_with_no_budgets(self):
        host = self.Host.create({})
        self.assertFalse(host.has_budget)
        self.assertFalse(host.budget_state)

    def test_has_budget_and_budget_state_once_a_budget_is_added(self):
        host = self.Host.create({})
        self.Document.create({'host_id': host.id})
        self.assertTrue(host.has_budget)
        self.assertEqual(host.budget_state, 'draft')

    def test_budget_state_tracks_the_active_budget_through_confirm_and_close(self):
        host = self.Host.create({})
        budget = self.Document.create({'host_id': host.id})

        budget.action_confirm()
        self.assertEqual(host.budget_state, 'confirmed')

        budget.action_close()
        self.assertEqual(host.budget_state, 'closed')

    def test_document_create_assigns_a_reference_when_none_given(self):
        budget = self.Document.create({})
        self.assertTrue(budget.name)
        self.assertNotEqual(budget.name, False)

    def test_document_create_keeps_an_explicit_reference(self):
        budget = self.Document.create({'name': 'EXPLICIT-REF'})
        self.assertEqual(budget.name, 'EXPLICIT-REF')

    def test_open_budget_action_raises_without_a_budget(self):
        host = self.Host.create({})
        with self.assertRaises(ValidationError):
            host._bridge_open_budget_action(host.budget_id)

    def test_open_budget_action_returns_an_action_for_a_real_budget(self):
        host = self.Host.create({})
        budget = self.Document.create({'host_id': host.id})

        action = host._bridge_open_budget_action(budget)

        self.assertEqual(action['res_model'], 'budget.flag.test.document')
        self.assertEqual(action['res_id'], budget.id)
