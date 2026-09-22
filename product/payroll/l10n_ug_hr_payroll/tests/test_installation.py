from datetime import date
from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestUgandaPayrollInstallation(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.structure = cls.env.ref(
            "l10n_ug_hr_payroll.structure_monthly"
        )
        cls.structure_type = cls.env.ref(
            "l10n_ug_hr_payroll.structure_type_employee"
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

    def test_uganda_payroll_parameters_are_date_effective(self):
        parameters = self.env['hr.rule.parameter']

        bands = parameters._get_parameter_from_code(
            'ele_ug_resident_paye_bands',
            date(2026, 7, 1),
        )

        surcharge_threshold = parameters._get_parameter_from_code(
            'ele_ug_paye_surcharge_threshold',
            date(2026, 7, 1)
        )

        surcharge_rate = parameters._get_parameter_from_code(
            'ele_ug_paye_surcharge_rate',
            date(2026, 7, 1)
        )

        employee_nssf_rate = parameters._get_parameter_from_code(
            'ele_ug_nssf_employee_rate',
            date(2026, 7, 1)
        )

        employer_nssf_rate = parameters._get_parameter_from_code(
            'ele_ug_nssf_employer_rate',
            date(2026, 7, 1)
        )

        self.assertEqual(
            bands,
            [
                (0, 335000, 0),
                (335000, 410000, 0.20),
                (410000, 485000, 0.25),
                (485000, 10000000, 0.30),
                (10000000, None, 0.30)
            ],
        )

        self.assertEqual(surcharge_threshold, 10000000)
        self.assertEqual(surcharge_rate, 0.10)
        self.assertEqual(employee_nssf_rate, 0.05)
        self.assertEqual(employer_nssf_rate, 0.10)

    def test_uganda_payroll_parameters_are_not_used_before_effective_date(self):
        value = self.env['hr.rule.parameter']._get_parameter_from_code(
            'ele_ug_resident_paye_bands',
            date(2026, 6, 30),
            raise_if_not_found=False
        )

        self.assertIsNone(value)

    def test_uganda_salary_rules_installed(self):
        expected_codes = {
            "BASIC",
            "ELE_UG_CASH_ALW",
            "ELE_UG_BENEFIT",
            "GROSS",
            "ELE_UG_TAXABLE",
            "ELE_UG_CHARGEABLE",
            "ELE_UG_NSSF_EMPLOYEE",
            "ELE_UG_PAYE",
            "ELE_UG_LST",
            "ELE_UG_OTHER_DED",
            "ELE_UG_NSSF_EMPLOYER",
            "ELE_UG_REIMBURSE",
            "NET",
        }

        actual_codes = set(self.structure.rule_ids.mapped('code'))

        self.assertTrue(
            expected_codes.issubset(actual_codes),
            f"Missing Uganda Salary rules: {sorted(expected_codes - actual_codes)}",
        )