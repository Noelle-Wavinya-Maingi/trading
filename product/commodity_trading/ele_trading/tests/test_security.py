from odoo.exceptions import AccessError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase, new_test_user


@tagged('post_install', '-at_install')
class TestTradeSecurity(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_a = cls.env.company
        cls.company_b = cls.env['res.company'].create({'name': 'Trade Security B'})
        cls.trader = new_test_user(
            cls.env, login='security_trader',
            groups='base.group_user,ele_trading.group_trading_trader',
            company_id=cls.company_a.id,
            company_ids=[(6, 0, [cls.company_a.id, cls.company_b.id])],
        )
        product = cls.env['product.product'].create({'name': 'Security commodity'})
        cls.trade = cls.env['trading.trade'].with_company(cls.company_b).create({
            'product_id': product.id, 'ele_trade_type': 'long',
        })
        cls.step = cls.env['trading.trade.step'].create({'name': 'Security step', 'ele_trade_id': cls.trade.id})

    def test_trade_and_child_are_hidden_outside_selected_company(self):
        for record in (self.trade, self.step):
            restricted = record.with_user(self.trader).with_context(allowed_company_ids=[self.company_a.id])
            with self.subTest(model=record._name), self.assertRaises(AccessError):
                restricted.read(['name'])
            with self.subTest(model=record._name), self.assertRaises(AccessError):
                restricted.write({'name': 'Forbidden edit'})

    def test_both_companies_allow_direct_child_access(self):
        step = self.step.with_user(self.trader).with_context(
            allowed_company_ids=[self.company_a.id, self.company_b.id],
        )
        self.assertEqual(step.name, 'Security step')

    def test_trader_cannot_delete_trade(self):
        with self.assertRaises(AccessError):
            self.trade.with_user(self.trader).with_context(
                allowed_company_ids=[self.company_b.id],
            ).unlink()

    def test_internal_user_without_trading_role_cannot_read_trade(self):
        user = new_test_user(self.env, login='no_trading_role', groups='base.group_user')
        with self.assertRaises(AccessError):
            self.trade.with_user(user).read(['name'])
