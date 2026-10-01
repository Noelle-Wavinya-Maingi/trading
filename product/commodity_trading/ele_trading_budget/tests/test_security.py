from odoo.exceptions import AccessError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase, new_test_user


@tagged('post_install', '-at_install')
class TestTradeBudgetSecurity(TransactionCase):
    def test_budget_and_line_reject_access_from_another_company(self):
        company_a = self.env.company
        company_b = self.env['res.company'].create({'name': 'Budget bridge B'})
        user = new_test_user(
            self.env, login='budget_bridge_trader',
            groups='base.group_user,ele_trading.group_trading_trader',
            company_id=company_a.id, company_ids=[(6, 0, [company_a.id, company_b.id])],
        )
        product = self.env['product.product'].create({'name': 'Budget security product'})
        trade = self.env['trading.trade'].with_company(company_b).create({
            'product_id': product.id, 'ele_trade_type': 'long',
        })
        budget = self.env['trading.trade.budget'].with_company(company_b).create({
            'ele_trade_id': trade.id, 'currency_id': company_b.currency_id.id,
        })
        line = self.env['operations.budget.line'].with_company(company_b).create({
            'name': 'Protected cost', 'ele_trade_budget_id': budget.id,
            'budgeted_amount': 10.0,
        })
        for record in (budget, line):
            restricted = record.with_user(user).with_context(allowed_company_ids=[company_a.id])
            with self.subTest(model=record._name), self.assertRaises(AccessError):
                restricted.read(['name'])
            with self.subTest(model=record._name), self.assertRaises(AccessError):
                restricted.write({'name': 'Forbidden'})
