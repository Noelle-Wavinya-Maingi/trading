from datetime import date


# Executed inside `odoo-bin shell`, where `env` is provided.
trade = env['trading.trade'].search([('name', '=', 'DEMO-CLOSED-SHEA')], limit=1)
budget = trade.budget_id

# Remove the artificial seed lines. Unlinking also reverses their previous
# direct contribution to the trade's additional-cost/revenue ledger.
budget.ele_budget_line_ids.unlink()
budget.state = 'confirmed'

supplier = env['res.partner'].search([('name', '=', 'Lakeview Cocoa Cooperative')], limit=1)
customer = env['res.partner'].search([('name', '=', 'Nairobi Chocolate Works')], limit=1)
expense_account = env['account.account'].search([('code', '=', '600000')], limit=1)
income_account = env['account.account'].search([('code', '=', '450000')], limit=1)

bill = env['account.move'].search([('ref', '=', 'SHEA-LOGISTICS-BILL')], limit=1)
if not bill:
    bill = env['account.move'].create({
        'move_type': 'in_invoice',
        'partner_id': supplier.id,
        'invoice_date': date.today(),
        'ref': 'SHEA-LOGISTICS-BILL',
        'currency_id': trade.currency_id.id,
        'ele_trade_id': trade.id,
        'invoice_line_ids': [
            (0, 0, {'name': 'Freight and handling', 'quantity': 1, 'price_unit': 5000.0, 'account_id': expense_account.id, 'tax_ids': [(5, 0, 0)]}),
            (0, 0, {'name': 'Quality inspection', 'quantity': 1, 'price_unit': 2500.0, 'account_id': expense_account.id, 'tax_ids': [(5, 0, 0)]}),
            (0, 0, {'name': 'Repackaging', 'quantity': 1, 'price_unit': 1500.0, 'account_id': expense_account.id, 'tax_ids': [(5, 0, 0)]}),
        ],
    })
    bill.action_post()

invoice = env['account.move'].search([('ref', '=', 'SHEA-QUALITY-PREMIUM')], limit=1)
if not invoice:
    invoice = env['account.move'].create({
        'move_type': 'out_invoice',
        'partner_id': customer.id,
        'invoice_date': date.today(),
        'ref': 'SHEA-QUALITY-PREMIUM',
        'currency_id': trade.currency_id.id,
        'ele_trade_id': trade.id,
        'invoice_line_ids': [(0, 0, {
            'name': 'Quality premium',
            'quantity': 1,
            'price_unit': 3000.0,
            'account_id': income_account.id,
            'tax_ids': [(5, 0, 0)],
        })],
    })
    invoice.action_post()

trade._compute_all_trade_fields()
budget.action_close()
env.cr.commit()

print('BILL', bill.name, bill.state, bill.amount_total)
print('INVOICE', invoice.name, invoice.state, invoice.amount_total)
print('BUDGET_LINES', budget.ele_budget_line_ids.mapped(lambda line: (line.name, line.actual_amount, line.source_reference.display_name)))
print('EXTRAS', trade.ele_additional_costs, trade.ele_additional_revenue)
print('PNL', trade.ele_realized_pnl, trade.ele_total_pnl)
