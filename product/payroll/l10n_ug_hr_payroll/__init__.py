from . import models


def _deactivate_copied_default_rules(env):
    """Keep historical lines but disable generic rules copied on structure creation."""
    structure = env.ref('l10n_ug_hr_payroll.structure_monthly')
    uganda_rules = env['hr.salary.rule'].browse([
        env.ref(f'l10n_ug_hr_payroll.{xmlid}').id
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


def post_init_hook(env):
    _deactivate_copied_default_rules(env)
