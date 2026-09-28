from datetime import date, timedelta


# Executed inside `odoo-bin shell`, where `env` is provided.
trade = env['trading.trade'].search([('name', '=', 'DEMO-CLOSED-SHEA')], limit=1)
product = trade.product_id
product.product_tmpl_id.write({'tracking': 'lot', 'is_storable': True})

supplier = env['res.partner'].search([('name', '=', 'Lakeview Cocoa Cooperative')], limit=1)
customer = env['res.partner'].search([('name', '=', 'Nairobi Chocolate Works')], limit=1)
eur = env['res.currency'].with_context(active_test=False).search([('name', '=', 'EUR')], limit=1)
usd = env['res.currency'].with_context(active_test=False).search([('name', '=', 'USD')], limit=1)
usd_pricelist = env['product.pricelist'].search([('name', '=', 'Commodity Export — USD')], limit=1)

trade.write({
    'ele_status': 'confirmed',
    'ele_additional_costs': 0.0,
    'ele_additional_revenue': 0.0,
    'ele_target_margin_percent': 10.0,
})

po = env['purchase.order'].search([('partner_ref', '=', 'FULL-SHEA-BUY')], limit=1)
if not po:
    po = env['purchase.order'].create({
        'partner_id': supplier.id,
        'partner_ref': 'FULL-SHEA-BUY',
        'date_order': date.today() - timedelta(days=40),
        'currency_id': eur.id,
        'ele_trade_id': trade.id,
        'order_line': [(0, 0, {
            'product_id': product.id,
            'name': 'Shea Butter — completed purchase',
            'product_qty': 120.0,
            'product_uom_id': product.uom_id.id,
            'price_unit': 6.0,
            'tax_ids': [(5, 0, 0)],
            'date_planned': date.today() - timedelta(days=32),
        })],
    })
    po.button_confirm()

lot = env['stock.lot'].search([('name', '=', 'SHEA-LOT-2026-001'), ('product_id', '=', product.id)], limit=1)
if not lot:
    lot = env['stock.lot'].create({
        'name': 'SHEA-LOT-2026-001',
        'product_id': product.id,
        'company_id': env.company.id,
    })
trade.ele_lot_ids = [(4, lot.id)]

so = env['sale.order'].search([('client_order_ref', '=', 'FULL-SHEA-SELL')], limit=1)
if not so:
    so = env['sale.order'].create({
        'partner_id': customer.id,
        'client_order_ref': 'FULL-SHEA-SELL',
        'date_order': date.today() - timedelta(days=20),
        'pricelist_id': usd_pricelist.id,
        'ele_trade_id': trade.id,
        'order_line': [(0, 0, {
            'product_id': product.id,
            'name': 'Shea Butter — completed export sale',
            'product_uom_qty': 120.0,
            'product_uom_id': product.uom_id.id,
            'price_unit': 7.5,
            'tax_ids': [(5, 0, 0)],
        })],
    })
    so.action_confirm()

budget = env['trading.trade.budget'].search([('ele_trade_id', '=', trade.id)], limit=1)
if not budget:
    budget = env['trading.trade.budget'].create({
        'ele_trade_id': trade.id,
        'currency_id': trade.currency_id.id,
    })
    Line = env['operations.budget.line'].with_context(skip_expense_update=True)
    base = {'ele_trade_budget_id': budget.id, 'currency_id': trade.currency_id.id}
    for values in (
        {'name': 'Commodity purchase — actual from linked PO', 'line_type': 'expense', 'budgeted_amount': 104400.0},
        {'name': 'Freight and handling', 'line_type': 'expense', 'budgeted_amount': 8500.0, 'actual_amount': 9000.0},
        {'name': 'Export sales — actual from linked SO', 'line_type': 'charge', 'budgeted_amount': 117000.0},
        {'name': 'Quality premium', 'line_type': 'charge', 'budgeted_amount': 3500.0, 'actual_amount': 3000.0},
    ):
        Line.create({**base, **values})
    budget.action_confirm()

trade._compute_all_trade_fields()
trade._auto_close_if_fully_matched()
budget.action_close()
env.cr.commit()

print('SHEA_FIXED', trade.ele_status, trade.ele_is_fully_matched)
print('DOCUMENTS', trade.ele_purchase_id.name, trade.ele_sale_order_ids.mapped('name'))
print('QUANTITIES', trade.quantity, trade.ele_total_sold_quantity, trade.ele_open_position_quantity)
print('PNL', trade.ele_realized_pnl, trade.ele_unrealized_pnl, trade.ele_total_pnl)
print('BUDGET', budget.name, budget.state)
