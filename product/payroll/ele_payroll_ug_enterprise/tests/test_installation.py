from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestUgandaPayrollInstallation(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.structure = cls.env.ref(
            'ele_payroll_ug_enterprise.structure_monthly'
        )
        cls.structure_type = cls.env.ref(
            'ele_payroll_ug_enterprise.structure_type_employee'
        )

    def test_structure_configuration(self):
        self.assertEqual(
            self.structure.country_id,
            self.env.ref('base.ug'),
        )
        self.assertEqual(self.structure.type_id, self.structure_type)
        self.assertEqual(
            self.structure_type.default_struct_id,
            self.structure,
        )
        self.assertEqual(
            self.structure_type.default_schedule_pay,
            'monthly',
        )
        self.assertEqual(
            self.structure_type.default_work_entry_type_id,
            self.env.ref('hr_work_entry.work_entry_type_attendance'),
        )

    def test_native_report_available(self):
        self.assertEqual(
            self.structure.report_id,
            self.env.ref('hr_payroll.action_report_payslip'),
        )

    def test_uganda_structure_recognized(self):
        slip = self.env['hr.payslip'].new({
            'struct_id': self.structure.id,
        })
        self.assertTrue(slip._ele_ug_is_localized())

    def test_native_structure_not_recognized_as_uganda(self):
        slip = self.env['hr.payslip'].new({
            'struct_id': self.env.ref(
                'hr_payroll.default_structure'
            ).id,
        })
        self.assertFalse(slip._ele_ug_is_localized())
        slip._ele_ug_check_supported()

    def test_missing_rules_block_calculation(self):
        self.structure.rule_ids.unlink()
        slip = self.env['hr.payslip'].new({
            'struct_id': self.structure.id,
        })
        with self.assertRaisesRegex(
            UserError,
            'Uganda salary rules are not configured',
        ):
            slip._get_payslip_lines()