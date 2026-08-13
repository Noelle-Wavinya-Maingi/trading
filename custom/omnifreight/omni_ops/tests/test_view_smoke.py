# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestOmniOpsFileViewSmoke(TransactionCase):
    """Odoo already validates view XML at module-install time, but that
    only surfaces as a registry-load crash a human has to read a traceback
    to diagnose -- this session hit that failure mode repeatedly (a broken
    xpath, a stray tag, a stale inherited view) while restructuring
    omni_ops_file_views.xml by hand. This test gives the same check a fast,
    readable pass/fail as part of the normal test run, and pins down the
    tab structure other modules (omni_budget, this module's own documents
    tab) rely on via the `extension_point_start` anchor -- see
    omni_ops_file_views.xml's comment on that page for why it exists."""

    def test_freight_file_form_loads_with_expected_tabs(self):
        view = self.env.ref('omni_ops.view_omni_ops_file_form')
        result = self.env['omni.ops.file'].get_view(view_id=view.id, view_type='form')
        arch = result['arch']

        for expected_name in (
            'extension_point_start', 'fob_steps', 'freight_steps', 'lod_steps',
        ):
            self.assertIn(
                f'name="{expected_name}"', arch,
                f"Expected page '{expected_name}' missing from the freight file form -- "
                "either it was renamed/removed, or the view failed to combine correctly."
            )

    def test_freight_file_list_view_loads(self):
        view = self.env.ref('omni_ops.view_omni_ops_file_list')
        self.env['omni.ops.file'].get_view(view_id=view.id, view_type='list')
