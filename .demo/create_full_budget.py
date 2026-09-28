from datetime import date


# Executed inside `odoo-bin shell`, where `env` is provided.
admin = env.ref('base.user_admin')
for xmlid in ('ele_trading_budget.group_budget_user', 'ele_trading_budget.group_budget_manager'):
    group = env.ref(xmlid, raise_if_not_found=False)
    if group:
        admin.write({'group_ids': [(4, group.id)]})

if not admin.employee_id:
    env['hr.employee'].create({'name': 'Demo Trader', 'user_id': admin.id})
if not env.user.employee_id:
    env['hr.employee'].create({'name': 'Demo Budget Processor', 'user_id': env.user.id})

trade = env['trading.trade'].search([('name', '=', 'DEMO-FULL-CASHEW')], limit=1)
budget = env['trading.trade.budget'].search([('ele_trade_id', '=', trade.id)], limit=1)

if not budget:
    # The line actuals below are the source of these additional amounts.
    trade.write({'ele_additional_costs': 0.0, 'ele_additional_revenue': 0.0})
    budget = env['trading.trade.budget'].create({
        'ele_trade_id': trade.id,
        'currency_id': trade.currency_id.id,
    })

    Line = env['operations.budget.line']
    base = {
        'ele_trade_budget_id': budget.id,
        'currency_id': trade.currency_id.id,
        'date_planned': date.today(),
        'date_actual': date.today(),
    }
    lines = [
        ('Commodity purchase — actual from PO P00002', 'expense', 130500.0, 0.0,
         'The planned value is shown here; the actual purchase value comes directly from linked PO P00002 and is included in Actual Cost above.'),
        ('Freight and handling', 'expense', 12000.0, 11000.0,
         'Inbound transport and handling for the cashew lot.'),
        ('Storage and inspection', 'expense', 6500.0, 7000.0,
         'Warehouse storage, inspection, and quality certification.'),
        ('Export sales — actual from SO S00002', 'charge', 105000.0, 0.0,
         'The planned value is shown here; actual sales revenue comes directly from linked SO S00002 and is included in Actual Revenue above.'),
        ('Quality premium', 'charge', 7000.0, 6500.0,
         'Additional premium earned for meeting the buyer quality specification.'),
    ]
    for name, line_type, planned, actual, description in lines:
        Line.create({
            **base,
            'name': name,
            'line_type': line_type,
            'budgeted_amount': planned,
            'actual_amount': actual,
            'description': description,
            'state': 'done' if actual else 'confirmed',
        })

    budget.action_confirm()
    trade._compute_all_trade_fields()
    env.cr.commit()

print('BUDGET_READY', budget.name, budget.state)
print('COST', budget.ele_total_budgeted_cost, budget.ele_actual_cost, budget.ele_cost_variance)
print('REVENUE', budget.ele_total_budgeted_revenue, budget.ele_actual_revenue, budget.ele_revenue_variance)
print('TRADE_EXTRAS', trade.ele_additional_costs, trade.ele_additional_revenue)
