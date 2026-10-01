from odoo.exceptions import AccessError, ValidationError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase, new_test_user


@tagged('post_install', '-at_install')
class TestBudgetLineSecurity(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_a = cls.env.company
        cls.company_b = cls.env['res.company'].create({'name': 'Budget Security B'})
        cls.user = new_test_user(
            cls.env, login='budget_security_user', groups='base.group_user',
            company_id=cls.company_a.id,
            company_ids=[(6, 0, [cls.company_a.id, cls.company_b.id])],
        )
        cls.line_a = cls.env['operations.budget.line'].with_company(cls.company_a).create({
            'name': 'Company A cost', 'actual_amount': 10, 'state': 'done',
        })
        cls.line_b = cls.env['operations.budget.line'].with_company(cls.company_b).create({
            'name': 'Company B cost',
        })

    def as_user(self, record, companies=None):
        return record.with_user(self.user).with_context(
            allowed_company_ids=companies or [self.company_a.id],
        )

    def test_user_cannot_forge_completed_line_sync(self):
        line = self.as_user(self.line_a)
        for token in (True, 'trusted', {'backend': True}):
            with self.subTest(token=token), self.assertRaises(ValidationError):
                line.with_context(budget_line_backend_sync=token).write({'actual_amount': 30})

    def test_user_can_edit_own_company_line_after_reopening(self):
        line = self.as_user(self.line_a)
        line.write({'state': 'confirmed'})
        line.write({'actual_amount': 12})
        self.assertEqual(line.actual_amount, 12)

    def test_direct_read_and_write_of_other_company_line_are_denied(self):
        line = self.as_user(self.line_b)
        with self.assertRaises(AccessError):
            line.read(['name'])
        with self.assertRaises(AccessError):
            line.write({'name': 'Unauthorized'})

    def test_company_selection_controls_search_and_direct_access(self):
        lines = self.as_user(self.env['operations.budget.line'])
        self.assertNotIn(self.line_b.id, lines.search([]).ids)
        both = self.as_user(self.line_b, [self.company_a.id, self.company_b.id])
        self.assertEqual(both.name, 'Company B cost')
        only_b = self.as_user(self.line_a, [self.company_b.id])
        with self.assertRaises(AccessError):
            only_b.read(['name'])

    def test_portal_user_cannot_read_budget_lines(self):
        portal = new_test_user(self.env, login='budget_portal', groups='base.group_portal')
        with self.assertRaises(AccessError):
            self.line_a.with_user(portal).read(['name'])

    def test_ordinary_user_can_create_a_line_in_selected_company(self):
        line = self.as_user(self.env['operations.budget.line']).create({'name': 'Own new line'})
        self.assertEqual(line.company_id, self.company_a)
