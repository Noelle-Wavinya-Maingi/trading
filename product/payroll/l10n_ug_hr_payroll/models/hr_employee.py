from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    ele_ug_tin = fields.Char(
        string='Uganda TIN', groups='hr_payroll.group_hr_payroll_user')
    ele_ug_nssf_number = fields.Char(
        string='Uganda NSSF number', groups='hr_payroll.group_hr_payroll_user')
    ele_ug_tax_treatment = fields.Selection(
        related='version_id.ele_ug_tax_treatment', readonly=False,
        inherited=True, groups='hr_payroll.group_hr_payroll_user')
    ele_ug_nssf_status = fields.Selection(
        related='version_id.ele_ug_nssf_status', readonly=False,
        inherited=True, groups='hr_payroll.group_hr_payroll_user')
    ele_ug_nssf_exemption_reason = fields.Char(
        related='version_id.ele_ug_nssf_exemption_reason', readonly=False,
        inherited=True, groups='hr_payroll.group_hr_payroll_user')
