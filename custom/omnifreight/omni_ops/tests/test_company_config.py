# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged

from ..models.res_company import DEFAULT_SERVICE_CATEGORY_NAME


@tagged('post_install', '-at_install')
class TestOmniCompanyConfig(TransactionCase):
    """The client-specific values that used to be hardcoded are now per-company
    configuration. Every resolver must (a) return the historical literal when
    nothing is configured, so existing installs are unaffected, and (b) honour
    the configured value once set, so a second freight client needs no code
    change. Both halves are asserted for each setting."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company

    # === service product category ===
    def test_service_category_falls_back_to_name_lookup(self):
        self.company.omni_service_category_id = False
        expected = self.env['product.category'].search(
            [('name', '=', DEFAULT_SERVICE_CATEGORY_NAME)], limit=1
        )
        self.assertEqual(self.company._omni_get_service_category(), expected)

    def test_service_category_uses_configured_value(self):
        category = self.env['product.category'].create({'name': 'Client Services'})
        self.company.omni_service_category_id = category
        self.assertEqual(self.company._omni_get_service_category(), category)

    # === workcenters ===
    def test_workcenter_uses_configured_value(self):
        workcenter = self.env['mrp.workcenter'].create({'name': 'Quay 7', 'code': 'Q7'})
        self.company.omni_fob_workcenter_id = workcenter
        self.assertEqual(self.company._omni_get_workcenter('fob'), workcenter)

    def test_workcenter_configured_value_wins_over_name_match(self):
        """A workcenter literally named 'fob' must not beat the configured one --
        this is the ambiguity the old `ilike` lookup suffered from."""
        self.env['mrp.workcenter'].create({'name': 'fob', 'code': 'FOBX'})
        configured = self.env['mrp.workcenter'].create({'name': 'Quay 9', 'code': 'Q9'})
        self.company.omni_freight_workcenter_id = configured
        self.assertEqual(self.company._omni_get_workcenter('freight'), configured)

    def test_workcenter_falls_back_to_creating_one(self):
        self.company.omni_lod_workcenter_id = False
        self.env['mrp.workcenter'].search([('name', 'ilike', 'lod')]).unlink()
        workcenter = self.company._omni_get_workcenter('lod')
        self.assertTrue(workcenter)
        self.assertEqual(workcenter.name, 'LOD Operations')

    def test_workcenter_empty_for_no_service_type(self):
        self.assertFalse(self.company._omni_get_workcenter(False))


@tagged('post_install', '-at_install')
class TestServiceScopeInference(TransactionCase):
    """The name-based scope guess is now only a fallback behind the product's
    explicit omni_service_scope, but its exact behaviour is pinned here because
    changing it would silently reassign the operations loaded onto existing BOMs."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Bom = cls.env['mrp.bom']

    def test_combined_scopes(self):
        infer = self.Bom._infer_service_scope_from_name
        self.assertEqual(infer('FOB Freight Destination service'), 'fob_freight_lod')
        self.assertEqual(infer('FOB and Freight'), 'fob_freight')
        self.assertEqual(infer('Freight to Destination'), 'freight_lod')
        self.assertEqual(infer('FOB to Destination'), 'fob_lod')

    def test_single_scopes(self):
        infer = self.Bom._infer_service_scope_from_name
        self.assertEqual(infer('FOB only'), 'fob')
        self.assertEqual(infer('Freight only'), 'freight')
        self.assertEqual(infer('Destination handling'), 'lod')
        self.assertEqual(infer('LOD handling'), 'lod')

    def test_no_match_returns_false(self):
        self.assertFalse(self.Bom._infer_service_scope_from_name('General service'))
        self.assertFalse(self.Bom._infer_service_scope_from_name(''))

    def test_legacy_lod_asymmetry_is_preserved(self):
        """'LOD' is only recognised on its own, never in a combination -- so this
        infers 'fob', not 'fob_lod'. Documented quirk, deliberately not fixed."""
        self.assertEqual(self.Bom._infer_service_scope_from_name('FOB LOD'), 'fob')
