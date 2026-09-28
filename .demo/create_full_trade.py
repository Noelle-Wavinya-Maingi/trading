from datetime import date, timedelta


# Executed inside `odoo-bin shell`, where `env` is provided.
Trade = env['trading.trade']
existing = Trade.search([('name', '=', 'DEMO-FULL-CASHEW')], limit=1)
if existing:
    print('FULL_TRADE_EXISTS', existing.id)
else:
    company = env.company
    eur = env['res.currency'].with_context(active_test=False).search([('name', '=', 'EUR')], limit=1)
    usd = env['res.currency'].with_context(active_test=False).search([('name', '=', 'USD')], limit=1)

    supplier = env['res.partner'].search([('name', '=', 'Lakeview Cocoa Cooperative')], limit=1)
    customer = env['res.partner'].search([('name', '=', 'Nairobi Chocolate Works')], limit=1)
    usd_pricelist = env['product.pricelist'].search([('name', '=', 'Commodity Export — USD')], limit=1)

    template = env['product.template'].search([('name', '=', 'Raw Cashew Nuts')], limit=1)
    if not template:
        template = env['product.template'].create({
            'name': 'Raw Cashew Nuts',
            'type': 'consu',
            'is_storable': True,
            'tracking': 'lot',
            'purchase_ok': True,
            'sale_ok': True,
            'ele_is_tradeable': True,
            'list_price': 13.0,
            'standard_price': 9.0,
        })
    product = template.product_variant_id

    po = env['purchase.order'].create({
        'partner_id': supplier.id,
        'partner_ref': 'FULL-CASHEW-BUY',
        'date_order': date.today() - timedelta(days=14),
        'currency_id': eur.id,
        'order_line': [(0, 0, {
            'product_id': product.id,
            'name': 'Raw Cashew Nuts — complete demo trade',
            'product_qty': 100.0,
            'product_uom_id': product.uom_id.id,
            'price_unit': 9.0,
            'tax_ids': [(5, 0, 0)],
            'date_planned': date.today() - timedelta(days=7),
        })],
    })
    po.button_confirm()
    trade = po.ele_trade_id
    trade.name = 'DEMO-FULL-CASHEW'

    lot = env['stock.lot'].create({
        'name': 'CASHEW-LOT-2026-001',
        'product_id': product.id,
        'company_id': company.id,
    })
    stock_location = env.ref('stock.stock_location_stock')
    env['stock.quant']._update_available_quantity(product, stock_location, 40.0, lot_id=lot)
    trade.ele_lot_ids = [(4, lot.id)]

    so = env['sale.order'].create({
        'partner_id': customer.id,
        'client_order_ref': 'FULL-CASHEW-SELL',
        'date_order': date.today() - timedelta(days=3),
        'pricelist_id': usd_pricelist.id,
        'ele_trade_id': trade.id,
        'order_line': [(0, 0, {
            'product_id': product.id,
            'name': 'Raw Cashew Nuts — partial export sale',
            'product_uom_qty': 60.0,
            'product_uom_id': product.uom_id.id,
            'price_unit': 13.0,
            'tax_ids': [(5, 0, 0)],
        })],
    })
    so.action_confirm()

    trade.write({
        'currency_id': company.currency_id.id,
        'ele_current_price': 12.0,
        'ele_current_price_currency_id': usd.id,
        'ele_additional_costs': 18000.0,
        'ele_additional_revenue': 6500.0,
        'ele_target_margin_percent': 18.0,
    })
    trade._compute_all_trade_fields()
    env.cr.commit()

    print('FULL_TRADE_READY', trade.id)
    print('TRADE', trade.name)
    print('LOT', lot.name, 'ON_HAND', trade.ele_on_hand_quantity)
    print('BUY', trade.quantity, trade.price, trade.ele_purchase_currency_id.name)
    print('SELL', trade.ele_total_sold_quantity, trade.ele_sales_price, trade.ele_sale_currency_id.name)
    print('EXTRAS', trade.ele_additional_costs, trade.ele_additional_revenue, trade.currency_id.name)
    print('PNL', trade.ele_realized_pnl, trade.ele_unrealized_pnl, trade.ele_total_pnl)
