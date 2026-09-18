from calendar import monthrange
from datetime import date
import math

from odoo import fields, models, _
from odoo.exceptions import UserError


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    ele_ug_lst_reviewed = fields.Boolean(
        string='Local service tax assessed', copy=False,
        groups='hr_payroll.group_hr_payroll_user',
        help='Confirm the council assessment and enter this month’s LST input, '
             'or confirm that no deduction is due. Annual assessment and '
             'collection scheduling are handled outside this initial addon.')

    def _ele_ug_is_localized(self):
        """Check if the payslip is using the Uganda payroll structure. This is used to determine whether to apply the Uganda payroll rules."""
        self.ensure_one()
        structure = self.env.ref('ele_payroll_ug_enterprise.structure_monthly', raise_if_not_found=False)

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
                raise UserError(_(
    'Uganda salary rules are not configured. '
    'Payroll cannot be calculated yet.'
))
            if not slip.date_from or not slip.date_to:
                raise UserError(_('Uganda payroll requires a complete monthly period.'))
            end = date(slip.date_from.year, slip.date_from.month,
                       monthrange(slip.date_from.year, slip.date_from.month)[1])
            if slip.date_from.day != 1 or slip.date_to != end:
                raise UserError(_('Uganda payroll currently supports full calendar months only.'))
            if not date(2026, 7, 1) <= slip.date_from <= date(2027, 6, 1):
                raise UserError(_('Uganda payroll currently supports July 2026 through June 2027.'))
            version = slip.version_id
            if slip.company_id.country_id.code != 'UG' or slip.currency_id.name != 'UGX':
                raise UserError(_('Uganda payroll requires a Ugandan company with UGX wages.'))
            if not version or version.ele_ug_tax_treatment != 'resident':
                raise UserError(_('Select resident tax treatment. Non-resident and multiple-employment payroll are not yet supported.'))
            if version.wage_type != 'monthly' or version.schedule_pay != 'monthly':
                raise UserError(_('Uganda payroll currently supports fixed monthly wages only.'))
            if (not version.contract_date_start or version.contract_date_start > slip.date_from
                    or (version.contract_date_end and version.contract_date_end < slip.date_to)
                    or slip.employee_id._get_version(slip.date_to) != version):
                raise UserError(_('Mid-month hiring, termination and version changes are not yet supported by Uganda payroll.'))
            if slip.credit_note or slip.is_refund_payslip:
                raise UserError(_('Uganda payroll refunds require a separate verified correction workflow.'))
            if version.ele_ug_nssf_status not in ('covered', 'exempt'):
                raise UserError(_('Select Uganda NSSF coverage before calculating payroll.'))
            if version.ele_ug_nssf_status == 'exempt' and not (version.ele_ug_nssf_exemption_reason or '').strip():
                raise UserError(_('Record the reason for the Uganda NSSF exemption.'))
            if not slip.ele_ug_lst_reviewed:
                raise UserError(_('Assess local service tax and confirm whether a deduction is due.'))
            allowed = {'ELE_UG_CASH_ALW', 'ELE_UG_BENEFIT', 'ELE_UG_REIMBURSE',
                       'ELE_UG_LST', 'ELE_UG_OTHER_DED'}
            for line in slip.input_line_ids:
                if line.code not in allowed or not math.isfinite(line.amount) or line.amount < 0:
                    raise UserError(_('Uganda payroll accepts only its supported non-negative inputs.'))
            if not math.isfinite(version.wage) or version.wage < 0:
                raise UserError(_('Uganda wages must be finite and non-negative.'))
            if any(line.is_paid is False and line.number_of_days for line in slip.worked_days_line_ids):
                raise UserError(_('Unpaid work entries are not yet supported by Uganda payroll.'))
            # Serialize calculations for this employee before checking monthly uniqueness.
            self.env.cr.execute('SELECT id FROM hr_employee WHERE id = %s FOR UPDATE',
                                [slip.employee_id.id])
            if self.sudo().search_count([
                    ('id', '!=', slip.id), ('employee_id', '=', slip.employee_id.id),
                    ('state', '!=', 'cancel'), ('date_from', '<=', slip.date_to),
                    ('date_to', '>=', slip.date_from),
                    ('struct_id', '=', slip.struct_id.id)], limit=1):
                raise UserError(_('Only one Uganda payslip per employee and month is supported. Cancel the duplicate first.'))
            if self.env['hr.salary.attachment'].sudo().search_count([
                    ('employee_ids', 'in', slip.employee_id.ids), ('state', '=', 'open')], limit=1):
                raise UserError(_('Salary adjustments are not yet supported by Uganda payroll.'))

    def _ele_ug_paye(self, chargeable):
        """Calculate the Uganda PAYE tax for a given chargeable amount. This is used to compute the PAYE tax based on the Uganda tax bands and surcharge rules."""
        self.ensure_one()
        bands = self._rule_parameter('ele_ug_resident_bands')
        tax = sum(max(0, min(chargeable, upper) - lower) * rate
                  for lower, upper, rate in bands)
        tax += max(0, chargeable - self._rule_parameter('ele_ug_surcharge_threshold')) * self._rule_parameter('ele_ug_surcharge_rate')
        return self.currency_id.round(tax)

    def _get_payslip_lines(self):
        """Override the payslip lines to apply Uganda payroll rules. This is used to ensure that the payslip lines are calculated according to the Uganda payroll requirements."""
        self._ele_ug_check_supported()
        return super()._get_payslip_lines()

    def action_payslip_done(self):
        """Override the payslip done action to apply Uganda payroll rules. This is used to ensure that the payslip is finalized according to the Uganda payroll requirements."""
        self._ele_ug_check_supported()
        return super().action_payslip_done()
