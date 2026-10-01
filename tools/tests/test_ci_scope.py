"""Selection regressions; these tests need neither Odoo nor PostgreSQL."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ci_scope import affected, manifests, scenarios  # noqa: E402


class TestScope(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.modules = manifests()

    def select(self, *paths):
        return affected(paths, self.modules)[1]

    def test_docs_only_skip_runtime(self):
        self.assertEqual(self.select('README.md', 'shared/budgets/README.md'), set())

    def test_ap_change_only_runs_ap(self):
        selected = self.select('product/ap_validation/ele_ap_validation/models/account_move.py')
        self.assertEqual(selected, {'ele_ap_validation'})
        self.assertEqual([r[0] for r in scenarios(selected, self.modules, 'community')],
                         ['ele_ap_validation_alone'])
        self.assertEqual(scenarios(selected, self.modules, 'enterprise'), [])

    def test_payroll_calculation_change_selects_both_editions(self):
        selected = self.select('product/payroll/ele_payroll_ug/models/ele_calculations.py')
        self.assertEqual(selected, {'ele_payroll_ug', 'l10n_ug_hr_payroll'})
        self.assertEqual([r[0] for r in scenarios(selected, self.modules, 'community')],
                         ['ele_payroll_ug_alone'])
        self.assertEqual([r[0] for r in scenarios(selected, self.modules, 'enterprise')],
                         ['l10n_ug_hr_payroll_alone'])

    def test_payroll_localization_change_only_runs_enterprise(self):
        selected = self.select('product/payroll/l10n_ug_hr_payroll/models/hr_payslip.py')
        self.assertEqual(selected, {'l10n_ug_hr_payroll'})
        self.assertEqual(scenarios(selected, self.modules, 'community'), [])

    def test_bank_change_only_runs_enterprise(self):
        selected = self.select('product/bank_reconciliation/ele_bank_reconcile/views/test.xml')
        self.assertEqual(selected, {'ele_bank_reconcile'})
        self.assertEqual(scenarios(selected, self.modules, 'community'), [])
        self.assertEqual([r[0] for r in scenarios(selected, self.modules, 'enterprise')],
                         ['ele_bank_reconcile_alone'])

    def test_shared_change_only_selects_its_consumers(self):
        selected = self.select('shared/budgets/models/operations_budget_line.py')
        self.assertEqual(selected, {'budgets', 'budgets_hr_expense', 'ele_trading_budget', 'omni_budget'})

    def test_trading_change_includes_budget_consumer_and_collision_check(self):
        selected = self.select('product/commodity_trading/ele_trading/models/sale_order.py')
        self.assertEqual(selected, {'ele_trading', 'ele_trading_budget'})
        rows = scenarios(selected, self.modules, 'community')
        self.assertIn('bridge_collision_regression', [r[0] for r in rows])
        self.assertFalse(any('ele_ap_validation' in r[1] for r in rows))

    def test_quotation_change_includes_transitive_consumers(self):
        self.assertEqual(self.select('custom/omnifreight/quotation/views/menu.xml'),
                         {'quotation', 'omni_ops', 'omni_budget'})

    def test_new_addon_is_discovered_without_workflow_filter(self):
        modules = dict(self.modules, ele_new={'path': 'product/new/ele_new', 'depends': ['base']})
        self.assertEqual(affected(['product/new/ele_new/__manifest__.py'], modules)[1], {'ele_new'})

    def test_removed_dependency_uses_previous_graph(self):
        old = {'ele_base': {'path': 'shared/ele_base', 'depends': []},
               'ele_client': {'path': 'custom/client/ele_client', 'depends': ['ele_base']}}
        new = {'ele_client': {'path': 'custom/client/ele_client', 'depends': []}}
        self.assertEqual(affected(['shared/ele_base/__manifest__.py'], new, old)[1], {'ele_client'})

    def test_moved_file_selects_both_addons(self):
        selected = self.select('shared/dispatch/models/old.py', 'shared/workflow/models/new.py')
        self.assertTrue({'dispatch', 'workflow', 'quotation', 'ele_trading'} <= selected)

    def test_runtime_tool_change_selects_full_suite(self):
        self.assertEqual(self.select('tools/verify_boundaries.sh'), set(self.modules))

    def test_static_tool_change_does_not_install_addons(self):
        self.assertEqual(self.select('tools/check_extension_collisions.py'), set())

    def test_shared_tests_keep_standalone_databases(self):
        for row in scenarios({'budgets', 'budgets_hr_expense'}, self.modules, 'community'):
            self.assertEqual(len(row[1]), 1)
            self.assertIn('omni_budget', row[3])


if __name__ == '__main__':
    unittest.main()


class TestUpgradeSelection(unittest.TestCase):
    def test_shared_data_change_upgrades_consumers_without_omnifreight(self):
        from ci_scope import upgrade_targets
        self.assertEqual(
            upgrade_targets(['shared/budgets/models/operations_budget_line.py'], manifests()),
            {'budgets', 'budgets_hr_expense', 'ele_trading_budget'},
        )

    def test_test_only_and_tooling_changes_skip_upgrades(self):
        from ci_scope import upgrade_targets
        self.assertEqual(upgrade_targets([
            'shared/budgets/tests/test_security.py', 'tools/verify_boundaries.sh',
        ], manifests()), set())
