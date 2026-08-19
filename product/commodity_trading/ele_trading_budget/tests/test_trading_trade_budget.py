# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestTradingTradeBudget(TransactionCase):
    """Exercises trading_trade_budget.py's state machine and totals, plus
    operations_budget_line.py's (trading_budget's own extension) push of a
    budget line's actual_amount into the trade's additional_costs/
    additional_revenue ledger -- the same "sync bridge" pattern
    budgets_hr_expense uses for hr.expense, but here feeding trading.trade
    directly instead of creating an external document."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product = cls.env['product.product'].create({
            'name': 'Test Commodity',
            'type': 'consu',
        })
        # _create_expense_from_budget_line() (budgets_hr_expense, a
        # dependency of trading_budget) requires the current user to have an
        # employee record -- every budget line with a positive expense-type
        # actual_amount also auto-creates an hr.expense alongside pushing the
        # amount into the trade, so this is needed even though these tests
        # are about the trade side of that sync, not the expense side.
        cls.env['hr.employee'].create({
            'name': 'Test Employee',
            'user_id': cls.env.user.id,
        })

    def _create_trade(self, trade_type='long', **vals):
        base_vals = {
            'trade_type': trade_type,
            'product_id': self.product.id,
        }
        base_vals.update(vals)
        return self.env['trading.trade'].create(base_vals)

    def _create_budget(self, trade):
        return self.env['trading.trade.budget'].create({
            'ele_trade_id': trade.id,
            'currency_id': trade.currency_id.id,
        })

    # ------------------------------------------------------------------
    # create() / state machine.
    # ------------------------------------------------------------------
    def test_create_assigns_budget_sequence_name(self):
        trade = self._create_trade()
        budget = self._create_budget(trade)
        self.assertTrue(budget.name.startswith('TRD/BUD/'))

    def test_action_confirm_and_close_transitions(self):
        trade = self._create_trade()
        budget = self._create_budget(trade)
        self.assertEqual(budget.state, 'draft')

        budget.action_confirm()
        self.assertEqual(budget.state, 'confirmed')

        budget.action_close()
        self.assertEqual(budget.state, 'closed')

    # ------------------------------------------------------------------
    # _compute_budgeted_totals: real lines override the quoted-margin
    # fallback used when no lines exist yet.
    # ------------------------------------------------------------------
    def test_budget_lines_override_the_quoted_margin_fallback(self):
        trade = self._create_trade(
            'long', quantity=100.0, price=10.0, target_margin_percent=20.0,
        )
        budget = self._create_budget(trade)
        # No lines yet -- falls back to the margin-derived quote.
        self.assertAlmostEqual(budget.total_budgeted_cost, 1000.0, places=2)

        self.env['operations.budget.line'].create({
            'name': 'Freight',
            'trade_budget_id': budget.id,
            'line_type': 'expense',
            'budgeted_amount': 250.0,
            'currency_id': trade.currency_id.id,
        })

        # A real line takes over entirely -- not added to the quote.
        self.assertAlmostEqual(budget.total_budgeted_cost, 250.0, places=2)

    # ------------------------------------------------------------------
    # _compute_actuals / _compute_variances mirror the trade's own ledger.
    # ------------------------------------------------------------------
    def test_actuals_and_variance_mirror_the_trade_ledger(self):
        trade = self._create_trade('long', quantity=10.0, price=100.0)
        budget = self._create_budget(trade)
        trade.write({'additional_costs': 50.0})

        self.assertAlmostEqual(budget.actual_cost, trade.total_purchase_cost + 50.0, places=2)
        self.assertAlmostEqual(budget.cost_variance, budget.actual_cost - budget.total_budgeted_cost, places=2)

    # ------------------------------------------------------------------
    # The actual sync bridge: a budget line's actual_amount feeds straight
    # into the trade's additional_costs/additional_revenue.
    # ------------------------------------------------------------------
    def test_expense_line_actual_amount_increases_trade_additional_costs(self):
        trade = self._create_trade()
        budget = self._create_budget(trade)

        line = self.env['operations.budget.line'].create({
            'name': 'Freight',
            'trade_budget_id': budget.id,
            'line_type': 'expense',
            'actual_amount': 40.0,
            'currency_id': trade.currency_id.id,
        })

        self.assertAlmostEqual(trade.additional_costs, 40.0, places=2)
        # The same positive expense-type actual_amount also backs an
        # hr.expense via budgets_hr_expense's own sync -- both mechanisms
        # fire off the same write, independently of each other.
        self.assertTrue(line.expense_id)

    def test_charge_line_actual_amount_increases_trade_additional_revenue(self):
        trade = self._create_trade()
        budget = self._create_budget(trade)

        self.env['operations.budget.line'].create({
            'name': 'Demurrage recovered',
            'trade_budget_id': budget.id,
            'line_type': 'charge',
            'actual_amount': 30.0,
            'currency_id': trade.currency_id.id,
        })

        self.assertAlmostEqual(trade.additional_revenue, 30.0, places=2)

    def test_reducing_actual_amount_adjusts_trade_ledger_without_double_counting(self):
        trade = self._create_trade()
        budget = self._create_budget(trade)
        line = self.env['operations.budget.line'].create({
            'name': 'Freight',
            'trade_budget_id': budget.id,
            'line_type': 'expense',
            'actual_amount': 40.0,
            'currency_id': trade.currency_id.id,
        })
        self.assertAlmostEqual(trade.additional_costs, 40.0, places=2)

        line.write({'actual_amount': 15.0})

        self.assertAlmostEqual(trade.additional_costs, 15.0, places=2)

    def test_unlinking_line_reverses_its_contribution(self):
        trade = self._create_trade()
        budget = self._create_budget(trade)
        line = self.env['operations.budget.line'].create({
            'name': 'Freight',
            'trade_budget_id': budget.id,
            'line_type': 'expense',
            'actual_amount': 40.0,
            'currency_id': trade.currency_id.id,
        })
        self.assertAlmostEqual(trade.additional_costs, 40.0, places=2)

        line.unlink()

        self.assertAlmostEqual(trade.additional_costs, 0.0, places=2)

    def test_two_lines_on_the_same_trade_do_not_clobber_each_other(self):
        """Each line tracks its own contribution (pnl_contributed_amount) so
        removing one must not also undo the other's."""
        trade = self._create_trade()
        budget = self._create_budget(trade)
        line_a = self.env['operations.budget.line'].create({
            'name': 'Freight',
            'trade_budget_id': budget.id,
            'line_type': 'expense',
            'actual_amount': 40.0,
            'currency_id': trade.currency_id.id,
        })
        self.env['operations.budget.line'].create({
            'name': 'Storage',
            'trade_budget_id': budget.id,
            'line_type': 'expense',
            'actual_amount': 25.0,
            'currency_id': trade.currency_id.id,
        })
        self.assertAlmostEqual(trade.additional_costs, 65.0, places=2)

        line_a.unlink()

        self.assertAlmostEqual(trade.additional_costs, 25.0, places=2)
