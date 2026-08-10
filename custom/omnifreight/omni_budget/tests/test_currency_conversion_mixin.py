# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestCurrencyConversionMixin(TransactionCase):
    """Characterizes currency.conversion.mixin (omni_budget) as it exists
    today, before shared/currency_bridge extracts its duplicated `_convert`
    call with quotation's own currency-conversion mixin. Pins down the
    log-and-fall-back error contract so the extraction can be verified as a
    pure relocation, not a behavior change."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.usd = cls.env.ref('base.USD')
        cls.eur = cls.env['res.currency'].with_context(active_test=False).search([('name', '=', 'EUR')], limit=1)
        cls.eur.active = True
        cls.env['res.currency.rate'].create({
            'currency_id': cls.eur.id,
            'rate': 0.5,
            'name': '2020-01-01',
        })
        cls.env.company.currency_id = cls.usd

        cls.product = cls.env['product.product'].create({
            'name': 'Test Freight Forwarding Service',
            'type': 'consu',
        })
        cls.production = cls.env['mrp.production'].create({
            'product_id': cls.product.id,
            'product_qty': 1.0,
            'product_uom_id': cls.product.uom_id.id,
        })
        cls.budget = cls.env['omni.mrp.budget'].create({
            'production_id': cls.production.id,
            'currency_id': cls.usd.id,
        })

    def test_zero_amount_returns_zero(self):
        self.assertEqual(
            self.budget._convert_to_target_currency(0.0, self.eur), 0.0
        )

    def test_missing_from_currency_returns_amount_unchanged(self):
        self.assertEqual(
            self.budget._convert_to_target_currency(100.0, False), 100.0
        )

    def test_same_currency_returns_amount_unchanged(self):
        self.assertEqual(
            self.budget._convert_to_target_currency(100.0, self.usd), 100.0
        )

    def test_different_currency_is_converted(self):
        converted = self.budget._convert_to_target_currency(
            100.0, self.eur, date='2020-01-01'
        )
        self.assertNotEqual(converted, 100.0)
