from calendar import monthrange
from datetime import date
import math

from odoo import models
from odoo.exceptions import UserError
from odoo.addons.ele_payroll_ug.models.ele_calculations import (  # pyright: ignore[reportMissingImports]
    nssf_contribution,
    resident_paye,
    lst_installment,
)


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    def _ele_ug_is_localized(self):
        """Check if the payslip is using the Uganda payroll structure. This is used to determine whether to apply the Uganda payroll rules."""
        self.ensure_one()
        structure = self.env.ref("ele_l10n_ug_hr_payroll.structure_monthly", raise_if_not_found=False,)

        return bool(structure and self.struct_id == structure)

    def _ele_ug_input(self, code):
        """Get the amount of a specific input code for this payslip. This is used to retrieve Uganda-specific inputs such as LST, cash allowance, benefits and reimbursements."""
        self.ensure_one()
        return sum(self.input_line_ids.filtered(lambda line: line.code == code).mapped('amount'))

    def _ele_ug_check_supported(self):
        """Check if the payslip is supported by the Uganda payroll rules. This is used to validate that the payslip meets the requirements for Uganda payroll calculations."""
        for slip in self:
            if not slip._ele_ug_is_localized():
                continue
            if not slip.struct_id.rule_ids:
                raise UserError(self.env._(
                    'Uganda salary rules are not configured. '
                    'Payroll cannot be calculated yet.'
                ))
            if not slip.date_from or not slip.date_to:
                raise UserError(self.env._('Uganda payroll requires a complete monthly period.'))
            end = date(slip.date_from.year, slip.date_from.month,
                       monthrange(slip.date_from.year, slip.date_from.month)[1])
            if slip.date_from.day != 1 or slip.date_to != end:
                raise UserError(self.env._('Uganda payroll currently supports full calendar months only.'))
            if slip.date_from < date(2026, 7, 1):
                raise UserError(self.env._('Uganda payroll does not support periods before July 2026'))
            version = slip.version_id
            if slip.company_id.country_id.code != 'UG' or slip.currency_id.name != 'UGX':
                raise UserError(self.env._('Uganda payroll requires a Ugandan company with UGX wages.'))
            if not version or version.ele_ug_tax_treatment != 'resident':
                raise UserError(self.env._('Select resident tax treatment. Non-resident and multiple-employment payroll are not yet supported.'))
            if version.wage_type != 'monthly' or version.schedule_pay != 'monthly':
                raise UserError(self.env._('Uganda payroll currently supports fixed monthly wages only.'))
            overlapping_versions = slip.employee_id._get_versions_with_contract_overlap_with_period(
                slip.date_from,
                slip.date_to,
            )
            if not version or version not in overlapping_versions:
                raise UserError(self.env._('The selected employee record must overlap the Uganda payroll month.'))
            if len(overlapping_versions) != 1:
                raise UserError(self.env._('Employment record changes within a Uganda payroll month are not yet supported.'))
            if slip.credit_note or slip.is_refund_payslip:
                raise UserError(self.env._('Uganda payroll refunds require a separate verified correction workflow.'))
            if version.ele_ug_nssf_status not in ('covered', 'exempt'):
                raise UserError(self.env._('Select Uganda NSSF coverage before calculating payroll.'))
            if version.ele_ug_nssf_status == 'exempt' and not (version.ele_ug_nssf_exemption_reason or '').strip():
                raise UserError(self.env._('Record the reason for the Uganda NSSF exemption.'))
            allowed = {'ELE_UG_CASH_ALW', 'ELE_UG_BENEFIT', 'ELE_UG_REIMBURSE',
                       'ELE_UG_OTHER_DED'}
            for line in slip.input_line_ids:
                if line.code not in allowed or not math.isfinite(line.amount) or line.amount < 0:
                    raise UserError(self.env._('Uganda payroll accepts only its supported non-negative inputs.'))
            if not math.isfinite(version.wage) or version.wage < 0:
                raise UserError(self.env._('Uganda wages must be finite and non-negative.'))
            if any(
                line.is_paid is False
                and line.number_of_days
                and line.code != 'OUT'
                for line in slip.worked_days_line_ids
            ):
                raise UserError(self.env._('Unpaid work entries are not yet supported by Uganda payroll.'))
            # Serialize calculations for this employee before checking monthly uniqueness.
            self.env.cr.execute('SELECT id FROM hr_employee WHERE id = %s FOR UPDATE',
                                [slip.employee_id.id])
            if self.sudo().search_count([
                    ('id', '!=', slip.id), ('employee_id', '=', slip.employee_id.id),
                    ('state', '!=', 'cancel'), ('date_from', '<=', slip.date_to),
                    ('date_to', '>=', slip.date_from),
                    ('struct_id', '=', slip.struct_id.id)], limit=1):
                raise UserError(self.env._('Only one Uganda payslip per employee and month is supported. Cancel the duplicate first.'))
            if self.env['hr.salary.attachment'].sudo().search_count([
                    ('employee_ids', 'in', slip.employee_id.ids), ('state', '=', 'open')], limit=1):
                raise UserError(self.env._('Salary adjustments are not yet supported by Uganda payroll.'))

    def _ele_ug_paye(self, chargeable_income):
        """Calculate the Uganda PAYE tax for a given chargeable amount. This is used to compute the PAYE tax based on the Uganda tax bands and surcharge rules."""
        self.ensure_one()

        tax = resident_paye(
            chargeable_income=chargeable_income,
            bands=self._rule_parameter('ele_ug_resident_paye_bands'),
            surcharge_threshold=self._rule_parameter(
                'ele_ug_paye_surcharge_threshold'
            ),
            surcharge_rate=self._rule_parameter('ele_ug_paye_surcharge_rate'),
        )
        return self.currency_id.round(float(tax))

    def _ele_ug_nssf(self, wage_base, rate_parameter):
        """Calculate the Uganda NSSF."""
        self.ensure_one()

        contribution = nssf_contribution(
            wage_base=wage_base,
            rate=self._rule_parameter(rate_parameter),
        )
        return self.currency_id.round(float(contribution))

    def _ele_ug_lst(self, cash_gross, taxable_income):
        """Calculate the automatic LST installment for this payslip month"""
        self.ensure_one()

        amount = lst_installment(
            cash_gross=cash_gross,
            taxable_income=taxable_income,
            month=self.date_to.month,
            lst_bands=self._rule_parameter("ele_ug_lst_bands"),
            collection_months=self._rule_parameter("ele_ug_lst_collection_months"),
            installment_count=self._rule_parameter("ele_ug_lst_installment_count"),
            paye_bands=self._rule_parameter("ele_ug_resident_paye_bands"),
            surcharge_threshold=self._rule_parameter("ele_ug_paye_surcharge_threshold"),
            surcharge_rate=self._rule_parameter("ele_ug_paye_surcharge_rate"),
        )

        return self.currency_id.round(float(amount))

    def _get_payslip_lines(self):
        """Override the payslip lines to apply Uganda payroll rules. This is used to ensure that the payslip lines are calculated according to the Uganda payroll requirements."""
        self._ele_ug_check_supported()
        return super()._get_payslip_lines()

    def action_payslip_done(self):
        """Override the payslip done action to apply Uganda payroll rules. This is used to ensure that the payslip is finalized according to the Uganda payroll requirements."""
        self._ele_ug_check_supported()
        return super().action_payslip_done()
