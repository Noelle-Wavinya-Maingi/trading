from datetime import date

from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install', 'uganda_payroll_e2e')
class TestUgandaPayrollE2E(TransactionCase):
    """Exercise Uganda payroll through Odoo records, work entries and reports."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.group_ids |= cls.env.ref('hr_payroll.group_hr_payroll_manager')
        cls.ugx = cls.env.ref('base.UGX')
        cls.company = cls.env['res.company'].create({
            'name': 'Uganda Payroll E2E Company',
            'country_id': cls.env.ref('base.ug').id,
            'currency_id': cls.ugx.id,
        })
        cls.env = cls.env(context={
            **cls.env.context,
            'allowed_company_ids': cls.company.ids,
        })
        cls.structure = cls.env.ref('ele_l10n_ug_hr_payroll.structure_monthly')
        cls.structure_type = cls.env.ref('ele_l10n_ug_hr_payroll.structure_type_employee')
        cls.input_types = {
            code: cls.env.ref(xmlid)
            for code, xmlid in {
                'ELE_UG_CASH_ALW': 'ele_l10n_ug_hr_payroll.input_cash_allowance',
                'ELE_UG_BENEFIT': 'ele_l10n_ug_hr_payroll.input_taxable_benefit',
                'ELE_UG_REIMBURSE': 'ele_l10n_ug_hr_payroll.input_reimbursement',
                'ELE_UG_OTHER_DED': 'ele_l10n_ug_hr_payroll.input_other_deduction',
            }.items()
        }

    def _employee(self, name, wage=500000, start=date(2026, 1, 1), end=False,
                  nssf_status='covered', exemption_reason=False,
                  tax_treatment='resident'):
        employee = self.env['hr.employee'].create({
            'name': name,
            'company_id': self.company.id,
            'country_id': self.env.ref('base.ug').id,
            'date_version': start,
            'contract_date_start': start,
            'contract_date_end': end,
            'wage': wage,
            'structure_type_id': self.structure_type.id,
            'resource_calendar_id': self.company.resource_calendar_id.id,
            'ele_ug_tax_treatment': tax_treatment,
            'ele_ug_nssf_status': nssf_status,
            'ele_ug_nssf_exemption_reason': exemption_reason,
        })
        return employee

    def _payslip(self, employee, month=7, year=2026, inputs=None,
                 generate_work_entries=True):
        date_from = date(year, month, 1)
        date_to = date(year, month, 31) if month in (1, 3, 5, 7, 8, 10, 12) else date(year, month, 30)
        if month == 2:
            date_to = date(year, month, 29 if year % 4 == 0 else 28)
        if generate_work_entries:
            entries = employee.version_ids.generate_work_entries(date_from, date_to)
            entries.filtered(lambda entry: entry.state != 'validated').action_validate()
        slip = self.env['hr.payslip'].create({
            'name': f'{employee.name} {date_from:%B %Y}',
            'employee_id': employee.id,
            'version_id': employee.version_id.id,
            'struct_id': self.structure.id,
            'date_from': date_from,
            'date_to': date_to,
            'company_id': self.company.id,
        })
        for code, amount in (inputs or {}).items():
            line = slip.input_line_ids.filtered(lambda item: item.code == code)
            if line:
                line.amount = amount
            else:
                slip.input_line_ids = [Command.create({
                    'input_type_id': self.input_types[code].id,
                    'amount': amount,
                })]
        slip.compute_sheet()
        return slip

    @staticmethod
    def _amounts(slip):
        return {line.code: line.total for line in slip.line_ids}

    def test_full_employee_lifecycle_and_report(self):
        slip = self._payslip(self._employee('Full lifecycle'))
        amounts = self._amounts(slip)
        self.assertEqual(amounts['BASIC'], 500000)
        self.assertEqual(amounts['GROSS'], 500000)
        self.assertEqual(amounts['ELE_UG_TAXABLE'], 500000)
        self.assertEqual(amounts['ELE_UG_LST'], -7500)
        self.assertEqual(amounts['ELE_UG_CHARGEABLE'], 492500)
        self.assertEqual(amounts['ELE_UG_NSSF_EMPLOYEE'], -25000)
        self.assertEqual(amounts['ELE_UG_PAYE'], -36000)
        self.assertEqual(amounts['ELE_UG_NSSF_EMPLOYER'], 50000)
        self.assertEqual(amounts['NET'], 431500)

        original = amounts.copy()
        slip.compute_sheet()
        self.assertEqual(self._amounts(slip), original)
        slip.action_payslip_done()
        self.assertEqual(slip.state, 'validated')
        # Odoo deliberately falls back to HTML while its test runner owns the
        # only request thread. The standalone PDF smoke test covers wkhtmltopdf.
        report_content, report_type = self.env['ir.actions.report']._render_qweb_pdf(
            self.env.ref('hr_payroll.action_report_payslip'), slip.id,
        )
        self.assertEqual(report_type, 'html')
        self.assertIn(b'Full lifecycle', report_content)
        slip.action_payslip_paid()
        self.assertEqual(slip.state, 'paid')

    def test_paye_boundaries_and_future_period(self):
        expected = {
            335000: 0,
            410000: 15000,
            485000: 33750,
            500000: 38250,
            10000000: 2888250,
            11000000: 3288250,
        }
        for wage, paye in expected.items():
            slip = self._payslip(
                self._employee(f'PAYE boundary {wage}', wage=wage),
                month=11,
                year=2027,
            )
            amounts = self._amounts(slip)
            self.assertEqual(amounts['ELE_UG_LST'], 0)
            self.assertEqual(-amounts['ELE_UG_PAYE'], paye)

    def test_inputs_affect_the_correct_bases(self):
        scenarios = {
            'ELE_UG_CASH_ALW': {'GROSS': 600000, 'ELE_UG_TAXABLE': 600000, 'NET': 501750},
            'ELE_UG_BENEFIT': {'GROSS': 500000, 'ELE_UG_TAXABLE': 600000, 'NET': 406750},
            'ELE_UG_REIMBURSE': {'GROSS': 500000, 'ELE_UG_TAXABLE': 500000, 'NET': 536750},
            'ELE_UG_OTHER_DED': {'GROSS': 500000, 'ELE_UG_TAXABLE': 500000, 'NET': 336750},
        }
        for code, expected in scenarios.items():
            slip = self._payslip(
                self._employee(f'Input {code}'),
                month=11,
                inputs={code: 100000},
            )
            amounts = self._amounts(slip)
            for line_code, amount in expected.items():
                self.assertEqual(amounts[line_code], amount)

    def test_nssf_exemption(self):
        slip = self._payslip(self._employee(
            'NSSF exempt', nssf_status='exempt', exemption_reason='Approved exemption',
        ), month=11)
        amounts = self._amounts(slip)
        self.assertEqual(amounts.get('ELE_UG_NSSF_EMPLOYEE', 0), 0)
        self.assertEqual(amounts.get('ELE_UG_NSSF_EMPLOYER', 0), 0)
        self.assertEqual(amounts['NET'], 461750)

    def test_invalid_configuration_and_duplicate_are_blocked(self):
        missing_reason = self._employee('Missing NSSF reason', nssf_status='exempt')
        with self.assertRaisesRegex(UserError, 'reason'):
            self._payslip(missing_reason, month=11)

        nonresident = self._employee('Nonresident', tax_treatment='nonresident')
        with self.assertRaisesRegex(UserError, 'resident tax treatment'):
            self._payslip(nonresident, month=11)

        old_period = self._employee('Old period', start=date(2025, 1, 1))
        with self.assertRaisesRegex(UserError, 'before July 2026'):
            self._payslip(old_period, month=6)

        duplicate_employee = self._employee('Duplicate')
        self._payslip(duplicate_employee, month=11)
        with self.assertRaisesRegex(UserError, 'Only one Uganda payslip'):
            self._payslip(duplicate_employee, month=11, generate_work_entries=False)

    def test_mid_month_hire_and_termination_are_prorated(self):
        for name, start, end in (
            ('Mid month hire', date(2026, 7, 15), False),
            ('Mid month leaver', date(2026, 1, 1), date(2026, 7, 15)),
        ):
            slip = self._payslip(self._employee(name, start=start, end=end))
            amounts = self._amounts(slip)
            self.assertGreater(amounts['BASIC'], 0)
            self.assertLess(amounts['BASIC'], 500000)
            self.assertTrue(slip.worked_days_line_ids.filtered(lambda line: line.code == 'OUT'))
            self.assertEqual(amounts['GROSS'], amounts['BASIC'])
            self.assertAlmostEqual(
                amounts['ELE_UG_NSSF_EMPLOYER'],
                amounts['GROSS'] * 0.10,
                delta=0.5,
            )

    def test_multi_employee_payrun(self):
        employees = self.env['hr.employee']
        for number, wage in enumerate((500000, 1000000, 11000000), start=1):
            employee = self._employee(f'Batch employee {number}', wage=wage)
            employee.version_ids.generate_work_entries(date(2026, 11, 1), date(2026, 11, 30))
            employees |= employee
        payrun = self.env['hr.payslip.run'].create({
            'name': 'Uganda November 2026',
            'date_start': date(2026, 11, 1),
            'date_end': date(2026, 11, 30),
            'structure_id': self.structure.id,
            'company_id': self.company.id,
        })
        payrun.generate_payslips(employee_ids=employees.ids)
        self.assertEqual(len(payrun.slip_ids), 3)
        payrun.action_validate()
        self.assertEqual(set(payrun.slip_ids.mapped('state')), {'validated'})
        payrun.action_paid()
        self.assertEqual(set(payrun.slip_ids.mapped('state')), {'paid'})
