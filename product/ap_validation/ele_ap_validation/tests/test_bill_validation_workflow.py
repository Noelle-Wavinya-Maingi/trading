# -*- coding: utf-8 -*-
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestBillApproverGroup(TransactionCase):
    """The group allowed to validate a bill is configurable per company, falling
    back to Administration/Settings (base.group_erp_manager) when unset."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company

    def test_falls_back_to_erp_manager_when_unset(self):
        self.company.ele_bill_approver_group_id = False
        self.assertEqual(
            self.company._ele_get_bill_approver_group(),
            self.env.ref('base.group_erp_manager'),
        )

    def test_uses_configured_group(self):
        custom_group = self.env['res.groups'].create({'name': 'Test Approvers'})
        self.company.ele_bill_approver_group_id = custom_group
        self.assertEqual(self.company._ele_get_bill_approver_group(), custom_group)


@tagged('post_install', '-at_install')
class TestManagementValidation(TransactionCase):
    """draft -> awaiting_validation -> validated via the management route, plus
    rejection. These only touch account.move; no hr.expense involved."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env['res.partner'].create({'name': 'Test Vendor'})
        cls.product = cls.env['product.product'].create({'name': 'Test Service'})

    def _create_bill(self):
        return self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.partner.id,
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product.id,
                'quantity': 1,
                'price_unit': 100.0,
            })],
        })

    def test_send_for_management_validation_sets_status_and_schedules_activity(self):
        bill = self._create_bill()
        approver = self.env['res.users'].create({
            'name': 'Approver',
            'login': 'approver_mgmt_test',
        })

        bill.action_send_for_management_validation(management_user_id=approver, note='Please check')

        self.assertEqual(bill.ele_status, 'awaiting_validation')
        activity = bill.activity_ids
        self.assertEqual(len(activity), 1)
        self.assertEqual(activity.user_id, approver)

    def test_get_management_user_picks_highest_id_member_of_approver_group(self):
        bill = self._create_bill()
        group = self.env['res.groups'].create({'name': 'Approvers For Test'})
        first_user = self.env['res.users'].create({'name': 'First', 'login': 'first_approver_test'})
        second_user = self.env['res.users'].create({'name': 'Second', 'login': 'second_approver_test'})
        group.user_ids = [(6, 0, (first_user + second_user).ids)]
        bill.company_id.ele_bill_approver_group_id = group

        # "Last user wins" is documented, inherited behaviour -- the higher id,
        # not the order added, decides who gets notified.
        self.assertEqual(bill._get_management_user(), second_user)

    def test_action_set_status_validated_marks_validated_and_completes_activities(self):
        bill = self._create_bill()
        bill.action_send_for_management_validation()
        self.assertTrue(bill.activity_ids)

        bill.action_set_status_validated(note='Looks good')

        self.assertEqual(bill.ele_status, 'validated')
        self.assertFalse(bill.activity_ids.filtered(lambda a: not a.date_done))

    def test_action_reject_sets_status_and_posts_reason(self):
        bill = self._create_bill()
        bill.action_send_for_management_validation()

        bill.action_reject(rejection_reason='Wrong amount')

        self.assertEqual(bill.ele_status, 'rejected')
        rejection_messages = bill.message_ids.filtered(lambda m: 'Wrong amount' in (m.body or ''))
        self.assertTrue(rejection_messages)


@tagged('post_install', '-at_install')
class TestOperationsValidation(TransactionCase):
    """draft -> awaiting_validation via the operations route: an hr.expense is
    raised from the bill, and approving that expense validates the bill back."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env['res.partner'].create({'name': 'Test Vendor'})
        cls.product = cls.env['product.product'].create({'name': 'Test Service'})
        cls.env['hr.employee'].create({
            'name': 'Test Employee',
            'user_id': cls.env.user.id,
        })

    def _create_bill(self, ref='BILL-OPS-TEST'):
        return self.env['account.move'].create({
            'move_type': 'in_invoice',
            'ref': ref,
            'partner_id': self.partner.id,
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product.id,
                'quantity': 1,
                'price_unit': 250.0,
            })],
        })

    def test_send_for_operations_validation_creates_expense_with_bill_reference(self):
        bill = self._create_bill()

        bill.action_send_for_operations_validation()

        self.assertEqual(bill.ele_status, 'awaiting_validation')
        expense = self.env['hr.expense'].search([('ele_bill_reference', '=', bill.ref)])
        self.assertEqual(len(expense), 1)
        self.assertEqual(expense.payment_mode, 'company_account')
        # The amount is the bill lines' price_total (tax included), not price_unit --
        # compare against that rather than hardcoding a tax-sensitive figure.
        self.assertEqual(expense.total_amount, sum(bill.invoice_line_ids.mapped('price_total')))

    def test_send_for_operations_validation_does_not_duplicate_expense(self):
        bill = self._create_bill()

        bill.action_send_for_operations_validation()
        bill.action_send_for_operations_validation()

        expenses = self.env['hr.expense'].search([('ele_bill_reference', '=', bill.ref)])
        self.assertEqual(len(expenses), 1)

    def test_send_for_operations_validation_requires_employee_record(self):
        bill = self._create_bill()
        no_employee_user = self.env['res.users'].create({
            'name': 'No Employee',
            'login': 'no_employee_test',
        })

        with self.assertRaises(UserError):
            bill.with_user(no_employee_user).action_send_for_operations_validation()

    def test_expense_approval_validates_linked_bill(self):
        bill = self._create_bill()
        bill.action_send_for_operations_validation()
        expense = self.env['hr.expense'].search([('ele_bill_reference', '=', bill.ref)])

        expense.write({'approval_state': 'approved'})

        self.assertEqual(bill.ele_status, 'validated')

    def test_expense_approval_does_not_touch_unrelated_bill(self):
        bill = self._create_bill()
        bill.action_send_for_operations_validation()
        expense = self.env['hr.expense'].search([('ele_bill_reference', '=', bill.ref)])

        other_bill = self._create_bill(ref='BILL-OPS-TEST-OTHER')
        other_bill.action_send_for_management_validation()

        expense.write({'approval_state': 'approved'})

        self.assertEqual(other_bill.ele_status, 'awaiting_validation')

    def test_action_post_skips_move_creation_for_company_account_expense(self):
        bill = self._create_bill()
        bill.action_send_for_operations_validation()
        expense = self.env['hr.expense'].search([('ele_bill_reference', '=', bill.ref)])
        expense.write({'approval_state': 'approved'})

        # Must not raise, and must not attempt Odoo's own payment-move creation
        # for a company-account expense -- the linked bill is the real record.
        expense.action_post()

        self.assertFalse(expense.account_move_id)
        self.assertEqual(bill.ele_status, 'validated')


@tagged('post_install', '-at_install')
class TestValidationWizards(TransactionCase):
    """The two wizards are thin routers: they just call the account.move method
    matching whatever the user picked, with no branching logic of their own."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env['res.partner'].create({'name': 'Test Vendor'})
        cls.product = cls.env['product.product'].create({'name': 'Test Service'})
        cls.env['hr.employee'].create({
            'name': 'Test Employee',
            'user_id': cls.env.user.id,
        })

    def _create_bill(self):
        return self.env['account.move'].create({
            'move_type': 'in_invoice',
            'ref': 'BILL-WIZ-TEST',
            'partner_id': self.partner.id,
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product.id,
                'quantity': 1,
                'price_unit': 100.0,
            })],
        })

    def test_defaults_management_user_from_approver_group(self):
        group = self.env['res.groups'].create({'name': 'Wizard Approvers'})
        approver = self.env['res.users'].create({'name': 'Approver', 'login': 'wizard_approver_test'})
        group.user_ids = [(6, 0, approver.ids)]
        self.env.company.ele_bill_approver_group_id = group

        wizard = self.env['account.move.validation.wizard'].create({
            'move_id': self._create_bill().id,
        })

        self.assertEqual(wizard.management_user_id, approver)

    def test_confirm_routes_to_management_validation(self):
        bill = self._create_bill()
        wizard = self.env['account.move.validation.wizard'].create({
            'move_id': bill.id,
            'validation_type': 'management',
        })

        wizard.action_confirm()

        self.assertEqual(bill.ele_status, 'awaiting_validation')
        self.assertTrue(bill.activity_ids)

    def test_confirm_routes_to_operations_validation(self):
        bill = self._create_bill()
        wizard = self.env['account.move.validation.wizard'].create({
            'move_id': bill.id,
            'validation_type': 'operations',
        })

        wizard.action_confirm()

        self.assertEqual(bill.ele_status, 'awaiting_validation')
        self.assertTrue(self.env['hr.expense'].search([('ele_bill_reference', '=', bill.ref)]))

    def test_confirm_in_confirm_mode_validates_regardless_of_type(self):
        bill = self._create_bill()
        bill.action_send_for_management_validation()
        wizard = self.env['account.move.validation.wizard'].with_context(
            validation_confirm_mode=True
        ).create({
            'move_id': bill.id,
            'validation_type': 'operations',
        })

        wizard.action_confirm()

        # is_validation_confirm_mode short-circuits validation_type entirely --
        # this always calls action_set_status_validated, never the operations path.
        self.assertEqual(bill.ele_status, 'validated')
        self.assertFalse(self.env['hr.expense'].search([('ele_bill_reference', '=', bill.ref)]))

    def test_rejection_wizard_confirm_rejects_the_bill(self):
        bill = self._create_bill()
        bill.action_send_for_management_validation()
        wizard = self.env['account.move.rejection.wizard'].create({
            'move_id': bill.id,
            'rejection_reason': 'Duplicate bill',
        })

        wizard.action_confirm()

        self.assertEqual(bill.ele_status, 'rejected')
