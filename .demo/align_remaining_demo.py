from datetime import date, timedelta


Trade = env['trading.trade']
supplier = env['res.partner'].search([('name', '=', 'Lakeview Cocoa Cooperative')], limit=1)
customer = env['res.partner'].search([('name', '=', 'Nairobi Chocolate Works')], limit=1)
eur = env['res.currency'].with_context(active_test=False).search([('name', '=', 'EUR')], limit=1)
expense_account = env['account.account'].search([('code', '=', '600000')], limit=1)
income_account = env['account.account'].search([('code', '=', '450000')], limit=1)
stock_location = env.ref('stock.stock_location_stock')


def posted_bill(trade, ref, lines):
    move = env['account.move'].search([('ref', '=', ref)], limit=1)
    if not move:
        move = env['account.move'].create({
            'move_type': 'in_invoice', 'partner_id': supplier.id,
            'invoice_date': date.today(), 'ref': ref,
            'currency_id': trade.currency_id.id, 'ele_trade_id': trade.id,
            'invoice_line_ids': [(0, 0, {
                'name': name, 'quantity': 1, 'price_unit': amount,
                'account_id': expense_account.id, 'tax_ids': [(5, 0, 0)],
            }) for name, amount in lines],
        })
        move.action_post()
    return move


def posted_invoice(trade, ref, name, amount):
    move = env['account.move'].search([('ref', '=', ref)], limit=1)
    if not move:
        move = env['account.move'].create({
            'move_type': 'out_invoice', 'partner_id': customer.id,
            'invoice_date': date.today(), 'ref': ref,
            'currency_id': trade.currency_id.id, 'ele_trade_id': trade.id,
            'invoice_line_ids': [(0, 0, {
                'name': name, 'quantity': 1, 'price_unit': amount,
                'account_id': income_account.id, 'tax_ids': [(5, 0, 0)],
            })],
        })
        move.action_post()
    return move


# Open coffee: a real purchase-backed, fully stocked, unsold position.
coffee = Trade.search([('name', '=', 'DEMO-OPEN-COFFEE')], limit=1)
coffee.write({'ele_additional_costs': 0.0, 'ele_additional_revenue': 0.0})
coffee_po = env['purchase.order'].search([('partner_ref', '=', 'FULL-COFFEE-BUY')], limit=1)
if not coffee_po:
    coffee_po = env['purchase.order'].create({
        'partner_id': supplier.id, 'partner_ref': 'FULL-COFFEE-BUY',
        'date_order': date.today() - timedelta(days=10), 'currency_id': eur.id,
        'ele_trade_id': coffee.id,
        'order_line': [(0, 0, {
            'product_id': coffee.product_id.id, 'name': 'Arabica Coffee — open purchase',
            'product_qty': 250.0, 'product_uom_id': coffee.product_id.uom_id.id,
            'price_unit': 8.5, 'tax_ids': [(5, 0, 0)],
            'date_planned': date.today() - timedelta(days=5),
        })],
    })
    coffee_po.button_confirm()
coffee.product_id.product_tmpl_id.write({'tracking': 'lot', 'is_storable': True})
coffee_lot = env['stock.lot'].search([('name', '=', 'COFFEE-LOT-2026-001')], limit=1)
if not coffee_lot:
    coffee_lot = env['stock.lot'].create({'name': 'COFFEE-LOT-2026-001', 'product_id': coffee.product_id.id, 'company_id': env.company.id})
    env['stock.quant']._update_available_quantity(coffee.product_id, stock_location, 250.0, lot_id=coffee_lot)
coffee.ele_lot_ids = [(4, coffee_lot.id)]
coffee_budget = coffee.budget_id or env['trading.trade.budget'].create({'ele_trade_id': coffee.id, 'currency_id': coffee.currency_id.id})
posted_bill(coffee, 'COFFEE-LOGISTICS-BILL', [('Inbound freight', 8000.0), ('Quality inspection', 4500.0)])
coffee._compute_all_trade_fields()
coffee_budget.action_confirm()

# Partial cashew: replace manually seeded amounts with posted documents.
cashew = Trade.search([('name', '=', 'DEMO-FULL-CASHEW')], limit=1)
cashew_budget = cashew.budget_id
cashew_budget.ele_budget_line_ids.unlink()
cashew.write({'ele_additional_costs': 0.0, 'ele_additional_revenue': 0.0})
posted_bill(cashew, 'CASHEW-OPERATIONS-BILL', [
    ('Freight and handling', 10000.0),
    ('Storage and inspection', 5000.0),
    ('Repackaging', 3000.0),
])
posted_invoice(cashew, 'CASHEW-QUALITY-PREMIUM', 'Quality premium', 6500.0)
cashew._compute_all_trade_fields()
cashew_budget.state = 'confirmed'

env.cr.commit()
for trade in (coffee, cashew):
    print('ALIGNED', trade.name, trade.ele_status, trade.quantity, trade.ele_total_sold_quantity,
          trade.ele_open_position_quantity, trade.ele_on_hand_quantity,
          trade.ele_additional_costs, trade.ele_additional_revenue,
          trade.ele_total_pnl, trade.budget_id.name, trade.budget_id.state)
