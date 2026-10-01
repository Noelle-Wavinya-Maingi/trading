"""Executed by verify_upgrades.py inside an Odoo shell on disposable databases.

MODULE and PHASE are supplied by the runner. Fixtures deliberately avoid
Omnifreight. Concrete products get business records; abstract libraries get
an XML-ID-backed partner to check general database/metadata preservation.
"""
import json


def seed_fixture(env, module):
    records = []

    def remember(record, names):
        values = record.read(names)[0]
        values.pop('id')
        records.append({'model': record._name, 'id': record.id, 'values': values})
        return record

    partner = remember(env['res.partner'].create({'name': 'Elewa upgrade fixture'}), ['name'])
    env['ir.model.data'].create({
        'module': 'ele_ci_upgrade', 'name': 'partner', 'model': 'res.partner',
        'res_id': partner.id, 'noupdate': True,
    })
    if module in {'budgets', 'budgets_hr_expense'}:
        remember(env['operations.budget.line'].create({
            'name': 'Existing budget amount', 'line_type': 'charge',
            'budgeted_amount': 123.45, 'actual_amount': 100, 'state': 'confirmed',
        }), ['name', 'budgeted_amount', 'actual_amount', 'state'])
    elif module in {'ele_trading', 'ele_trading_budget'}:
        product = env['product.product'].create({'name': 'Upgrade commodity', 'type': 'consu'})
        trade = remember(env['trading.trade'].create({
            'product_id': product.id, 'ele_trade_type': 'long', 'quantity': 12, 'price': 25,
        }), ['name', 'quantity', 'price', 'product_id', 'company_id'])
        if module == 'ele_trading_budget':
            budget = remember(env['trading.trade.budget'].create({
                'ele_trade_id': trade.id, 'currency_id': trade.currency_id.id,
            }), ['name', 'ele_trade_id', 'currency_id'])
            remember(env['operations.budget.line'].create({
                'name': 'Existing trade budget', 'ele_trade_budget_id': budget.id,
                'line_type': 'charge', 'budgeted_amount': 80,
            }), ['name', 'ele_trade_budget_id', 'budgeted_amount'])
    elif module == 'ele_ap_validation':
        remember(env['account.move'].create({
            'move_type': 'in_invoice', 'partner_id': partner.id, 'ref': 'ELE-UPGRADE-BILL',
        }), ['ref', 'move_type', 'partner_id', 'state'])
    elif module == 'ele_bank_reconcile':
        journal = env['account.journal'].create({'name': 'Upgrade bank', 'code': 'EUP', 'type': 'bank'})
        remember(env['account.bank.statement.line'].create({
            'journal_id': journal.id, 'payment_ref': 'ELE-UPGRADE-BANK', 'amount': 42,
        }), ['payment_ref', 'amount', 'journal_id'])
    elif module not in {'dispatch', 'workflow', 'budget_flag'}:
        raise AssertionError(f'Add an upgrade fixture for {module} before shipping stored-data changes.')
    env['ir.config_parameter'].set_param('ele_ci_upgrade_fixture', json.dumps(records))
    # This shell runs outside an RPC and exists only to seed a disposable DB.
    env.cr.commit()


def check_fixture(env):
    records = json.loads(env['ir.config_parameter'].get_param('ele_ci_upgrade_fixture'))
    for spec in records:
        record = env[spec['model']].browse(spec['id']).exists()
        assert record, f"Upgrade lost {spec['model']} record {spec['id']}"
        values = record.read(list(spec['values']))[0]
        values.pop('id')
        # JSON normalizes Many2one tuples to lists on both sides.
        assert json.loads(json.dumps(values)) == spec['values'], (spec, values)
    assert env.ref('ele_ci_upgrade.partner').id == records[0]['id'], 'Fixture XML ID changed'
    print(f'Preserved {len(records)} fixture records and their XML ID.')


# Odoo shell supplies env; the runner supplies MODULE and PHASE.
if PHASE == 'seed':  # noqa: F821
    seed_fixture(env, MODULE)  # noqa: F821
else:
    check_fixture(env)  # noqa: F821
