import ast
import tempfile
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

import check_quality


class TestQualityGate(TestCase):
    def test_changed_source_is_not_hidden_by_an_existing_violation(self):
        old = [('flake8', 'a.py', 'E225', 'spacing', 'old=1')]
        new = [('flake8', 'a.py', 'E225', 'spacing', 'new=1')]
        self.assertTrue(check_quality.new_findings(new, old))
        self.assertFalse(check_quality.new_findings(old, old))

    def test_duplicate_new_violation_is_counted(self):
        item = ('flake8', 'a.py', 'E225', 'spacing', 'a=1')
        self.assertEqual(sum(check_quality.new_findings([item, item], [item]).values()), 1)

    def test_omni_is_outside_quality_scan(self):
        self.assertFalse(any('custom/omnifreight/' in str(p) for p in check_quality.files()))

    def test_naming_rejects_new_unprefixed_extension_field(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(check_quality, 'ROOT', Path(temp)):
            path = Path(temp) / 'product/ele_example/models/sale_order.py'
            path.parent.mkdir(parents=True)
            path.write_text("class SaleOrder:\n    _inherit = 'sale.order'\n    wrong_name = fields.Char()\n    ele_reference = fields.Char()\n")
            result = check_quality.naming_findings([path])
            self.assertEqual(len(result), 1)
            self.assertIn('wrong_name', result[0][-1])

    def test_shell_fixture_is_valid_python(self):
        ast.parse((check_quality.ROOT / 'tools/upgrade_fixture.py').read_text())

    def test_existing_model_and_standard_settings_keep_odoo_names(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(check_quality, 'ROOT', Path(temp)):
            path = Path(temp) / 'product/ele_example/models/extension.py'
            path.parent.mkdir(parents=True)
            path.write_text(
                "class SaleOrder:\n    _name = 'sale.order'\n    _inherit = ['sale.order', 'ele.mixin']\n"
                "class Settings:\n    _inherit = 'res.config.settings'\n    module_ele_example = fields.Boolean()\n"
            )
            self.assertEqual(check_quality.naming_findings([path]), [])
