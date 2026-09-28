from datetime import date


# Executed inside `odoo-bin shell`, where `env` is provided.
Currency = env['res.currency'].with_context(active_test=False)
Rate = env['res.currency.rate']

kes = Currency.search([('name', '=', 'KES')], limit=1)
usd = Currency.search([('name', '=', 'USD')], limit=1)
eur = Currency.search([('name', '=', 'EUR')], limit=1)

for currency in (kes, usd, eur):
    currency.active = True

company = env.company
company.currency_id = kes

# Odoo stores each foreign currency as units of that currency per KES.
# These round demo rates make the conversions easy to explain on screen:
#   1 USD = KES 130; 1 EUR = KES 145.
for currency, stored_rate in ((usd, 1.0 / 130.0), (eur, 1.0 / 145.0)):
    existing = Rate.search([
        ('currency_id', '=', currency.id),
        ('company_id', '=', company.id),
        ('name', '=', date.today()),
    ], limit=1)
    vals = {
        'currency_id': currency.id,
        'company_id': company.id,
        'name': date.today(),
        'rate': stored_rate,
    }
    if existing:
        existing.write(vals)
    else:
        Rate.create(vals)

supplier = env['res.partner'].search([('name', '=', 'Lakeview Cocoa Cooperative')], limit=1)
customer = env['res.partner'].search([('name', '=', 'Nairobi Chocolate Works')], limit=1)
supplier.property_purchase_currency_id = eur

usd_pricelist = env['product.pricelist'].search([
    ('name', '=', 'Commodity Export — USD'),
    ('company_id', 'in', [False, company.id]),
], limit=1)
if not usd_pricelist:
    usd_pricelist = env['product.pricelist'].create({
        'name': 'Commodity Export — USD',
        'currency_id': usd.id,
        'company_id': company.id,
    })
customer.property_product_pricelist = usd_pricelist

po = env['purchase.order'].search([('partner_ref', '=', 'DEMO-COCOA-BUY')], limit=1)
po.currency_id = eur
po.order_line.write({'price_unit': 10.0})

so = env['sale.order'].search([('client_order_ref', '=', 'DEMO-COCOA-SELL')], limit=1)
so.pricelist_id = usd_pricelist
so.order_line.write({'price_unit': 14.0})

trades = env['trading.trade'].search([('name', 'in', ['DEMO-OPEN-COFFEE', 'DEMO-CLOSED-SHEA'])])
trades.write({
    'currency_id': kes.id,
    'ele_purchase_currency_id': eur.id,
    'ele_current_price_currency_id': usd.id,
})

env.cr.commit()
print('MULTICURRENCY_READY')
print('REPORTING KES')
print('PURCHASE EUR', po.amount_total)
print('SALE USD', so.amount_total)
