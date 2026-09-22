from decimal import Decimal

from odoo.tests import tagged
from odoo.tests.common import BaseCase

from ..models.ele_calculations import (
    nssf_contribution,
    resident_paye,
    lst_installment
)


BANDS_2026 = (
    (0, 335000, Decimal('0')),
    (335000, 410000, Decimal('0.20')),
    (410000, 485000, Decimal('0.25')),
    (485000, 10000000, Decimal('0.30')),
    (10000000, None, Decimal("0.30")),
)
LST_BANDS = (
        (0, 100000, 0),
        (100000, 200000, 5000),
        (200000, 300000, 10000),
        (300000, 400000, 20000),
        (400000, 500000, 30000),
        (500000, 600000, 40000),
        (600000, 700000, 60000),
        (700000, 800000, 70000),
        (800000, 900000, 80000),
        (900000, 1000000, 90000),
        (1000000, None, 100000),
    )


@tagged('post_install', '-at_install')
class TestUgandaPayrollCalculations(BaseCase):

    def _paye(self, income):
        return resident_paye(
            income,
            BANDS_2026,
            surcharge_threshold=10000000,
            surcharge_rate=Decimal('0.10'),
        )

    def test_resident_paye_boundaries(self):
        expected = {
            335000: 0,
            410000: 15000,
            485000: 33750,
            500000: 38250,
            10000000: 2888250,
            11000000: 3288250,
        }

        for income, tax in expected.items():
            with self.subTest(income=income):
                self.assertEqual(self._paye(income), Decimal(tax))

    def test_ura_500000_example(self):
        self.assertEqual(
            self._paye(500000),
            Decimal('38250'),
        )

    def test_nssf_employee_contribution(self):
        self.assertEqual(
            nssf_contribution(500000, Decimal('0.05')),
            Decimal('25000'),
        )

    def test_nssf_employer_contribution(self):
        self.assertEqual(
            nssf_contribution(500000, Decimal('0.10')),
            Decimal('50000'),
        )

    def test_invalid_amounts_are_rejected(self):
        for value in (-1, 'invalid', 'NaN', 'Infinity'):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    nssf_contribution(value, Decimal('0.05'))




    def _lst(self, income, month):
        return lst_installment(
            cash_gross=income,
            taxable_income=income,
            month=month,
            lst_bands=LST_BANDS,
            collection_months=(7, 8, 9, 10),
            installment_count=4,
            paye_bands=BANDS_2026,
            surcharge_threshold=10000000,
            surcharge_rate=Decimal("0.10"),
        )


    def test_lst_for_one_million_in_collection_month(self):
        self.assertEqual(
            self._lst(1000000, 9),
            Decimal("20000"),
        )


    def test_lst_is_zero_outside_collection_months(self):
        self.assertEqual(
            self._lst(1000000, 11),
            Decimal("0"),
        )