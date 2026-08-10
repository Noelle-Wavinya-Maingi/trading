# -*- coding: utf-8 -*-
from unittest.mock import patch
from odoo.tests.common import TransactionCase
from odoo.tests import tagged
from odoo.exceptions import UserError


@tagged('post_install', '-at_install')
class TestCurrencyConversionMixin(TransactionCase):
    """Characterizes omnifreight.currency.conversion (quotation) as it
    exists today, before shared/currency_bridge extracts its duplicated
    `_convert` call with omni_budget's own currency-conversion mixin. Pins
    down the raise-on-failure error contract so the extraction can be
    verified as a pure relocation, not a behavior change."""

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

        cls.partner = cls.env['res.partner'].create({'name': 'Test Freight Customer'})
        cls.quotation = cls.env['sale.order'].create({
            'partner_id': cls.partner.id,
            'currency_id': cls.usd.id,
        })

    def test_zero_amount_returns_zero(self):
        self.assertEqual(
            self.quotation.convert_rate_amount(0.0, self.eur), 0.0
        )

    def test_missing_rate_currency_returns_zero(self):
        self.assertEqual(
            self.quotation.convert_rate_amount(100.0, False), 0.0
        )

    def test_same_currency_returns_amount_unchanged(self):
        self.assertEqual(
            self.quotation.convert_rate_amount(100.0, self.usd), 100.0
        )

    def test_different_currency_is_converted(self):
        converted = self.quotation.convert_rate_amount(100.0, self.eur)
        self.assertNotEqual(converted, 100.0)

    def test_conversion_failure_raises_user_error(self):
        # Forces the underlying `_convert` call to fail, to pin down that
        # this mixin re-wraps the failure as a UserError -- unlike
        # omni_budget's mixin, which logs and falls back to the original
        # amount instead.
        with patch(
            'odoo.addons.base.models.res_currency.Currency._convert',
            side_effect=Exception('boom'),
        ):
            with self.assertRaises(UserError):
                self.quotation.convert_rate_amount(100.0, self.eur)
