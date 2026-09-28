from datetime import date, timedelta


# This file is executed inside `odoo-bin shell`, where `env` is provided.
company = env.company
company.write({'name': 'Elewa Commodity Demo'})

admin = env.ref('base.user_admin')
admin.write({'password': 'demo'})
for xmlid in ('ele_trading.group_trading_trader', 'ele_trading.group_trading_manager'):
    group = env.ref(xmlid, raise_if_not_found=False)
    if group:
        admin.write({'group_ids': [(4, group.id)]})


def partner(name, supplier=False, customer=False):
    record = env['res.partner'].search([('name', '=', name)], limit=1)
    vals = {
        'name': name,
        'company_type': 'company',
        'email': name.lower().replace(' ', '.') + '@example.com',
    }
    if supplier:
        vals['supplier_rank'] = 1
    if customer:
        vals['customer_rank'] = 1
    return record.write(vals) and record or env['res.partner'].create(vals)


def product(name):
    template = env['product.template'].search([('name', '=', name)], limit=1)
    vals = {
        'name': name,
        'type': 'consu',
        'purchase_ok': True,
        'sale_ok': True,
        'ele_is_tradeable': True,
        'list_price': 14.0,
        'standard_price': 10.0,
    }
    if template:
        template.write(vals)
    else:
        template = env['product.template'].create(vals)
    return template.product_variant_id


supplier = partner('Lakeview Cocoa Cooperative', supplier=True)
customer = partner('Nairobi Chocolate Works', customer=True)
cocoa = product('Cocoa Beans')
coffee = product('Arabica Coffee')
shea = product('Shea Butter')

# A clean pair of draft orders for the live walkthrough.
po = env['purchase.order'].search([('partner_ref', '=', 'DEMO-COCOA-BUY')], limit=1)
if not po:
    po = env['purchase.order'].create({
        'partner_id': supplier.id,
        'partner_ref': 'DEMO-COCOA-BUY',
        'date_order': date.today(),
        'order_line': [(0, 0, {
            'product_id': cocoa.id,
            'name': 'Cocoa Beans — demo purchase',
            'product_qty': 100.0,
            'product_uom_id': cocoa.uom_id.id,
            'price_unit': 10.0,
            'date_planned': date.today() + timedelta(days=7),
        })],
    })

so = env['sale.order'].search([('client_order_ref', '=', 'DEMO-COCOA-SELL')], limit=1)
if not so:
    so = env['sale.order'].create({
        'partner_id': customer.id,
        'client_order_ref': 'DEMO-COCOA-SELL',
        'date_order': date.today(),
        'order_line': [(0, 0, {
            'product_id': cocoa.id,
            'name': 'Cocoa Beans — demo sale',
            'product_uom_qty': 40.0,
            'product_uom_id': cocoa.uom_id.id,
            'price_unit': 14.0,
        })],
    })

# Two representative records make the dashboard useful before the live action.
Trade = env['trading.trade']
if not Trade.search([('name', '=', 'DEMO-OPEN-COFFEE')], limit=1):
    Trade.create({
        'name': 'DEMO-OPEN-COFFEE',
        'ele_trade_type': 'long',
        'product_id': coffee.id,
        'quantity': 250.0,
        'price': 8.50,
        'ele_current_price': 10.20,
        'ele_additional_costs': 125.0,
        'ele_target_margin_percent': 20.0,
        'ele_status': 'confirmed',
    })

if not Trade.search([('name', '=', 'DEMO-CLOSED-SHEA')], limit=1):
    Trade.create({
        'name': 'DEMO-CLOSED-SHEA',
        'ele_trade_type': 'long',
        'product_id': shea.id,
        'quantity': 120.0,
        'price': 6.00,
        'ele_sales_price': 7.50,
        'ele_current_price': 7.50,
        'ele_additional_costs': 60.0,
        'ele_target_margin_percent': 15.0,
        'ele_status': 'closed',
    })

env.cr.commit()
print('DEMO_READY')
print('PURCHASE_ORDER', po.name)
print('SALE_ORDER', so.name)
print('LOGIN admin / demo')
