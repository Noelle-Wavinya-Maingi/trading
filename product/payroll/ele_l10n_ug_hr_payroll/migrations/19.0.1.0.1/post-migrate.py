from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    structure = env.ref('ele_l10n_ug_hr_payroll.structure_monthly')
    uganda_rules = env['hr.salary.rule'].browse([
        env.ref(f'ele_l10n_ug_hr_payroll.{xmlid}').id
        for xmlid in (
            'salary_rule_basic',
            'salary_rule_cash_gross',
            'salary_rule_net',
        )
    ])
    copied_rules = structure.rule_ids.filtered(
        lambda rule: rule.code in {'BASIC', 'GROSS', 'NET'}
        and rule not in uganda_rules
    )
    copied_rules.active = False
