from odoo import fields, models


class HrVersion(models.Model):
    _inherit = 'hr.version'

    ele_ug_tax_treatment = fields.Selection(
        [('resident', 'Resident'), ('nonresident', 'Non-resident'),
         ('multiple', 'Multiple employment')],
        string='Uganda tax treatment',
        groups='hr_payroll.group_hr_payroll_user', tracking=True,
        help='The initial localization supports resident single employment only.')
    ele_ug_nssf_status = fields.Selection(
        [('covered', 'Covered'), ('exempt', 'Exempt')],
        string='Uganda NSSF coverage',
        groups='hr_payroll.group_hr_payroll_user', tracking=True)
    ele_ug_nssf_exemption_reason = fields.Char(
        string='NSSF exemption reason',
        groups='hr_payroll.group_hr_payroll_user', tracking=True)
