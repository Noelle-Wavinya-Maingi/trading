# -*- coding: utf-8 -*-
from unittest.mock import patch

from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestDispatchMixin(TransactionCase):
    """Exercises _bridge_definitions()/_bridge_sync()/_bridge_run_definition()
    directly, against dispatch.test.host (see
    shared/dispatch/models/order_bridge_test_host.py for why a dummy
    model, not sale.order, is used here), with synthetic definitions
    standing in for two real verticals (e.g. omnifreight's and ele_trading's
    registrations on sale.order) -- proving the registry actually runs every
    registered definition independently, rather than relying on the two
    real verticals happening to both behave today."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Host = cls.env['dispatch.test.host']
        cls.Partner = cls.env['res.partner']

    def _definition(self, host, label):
        """A minimal but complete definition dict, tagged with `label` so
        assertions can tell which definition's create/link actually ran.
        Uses res.partner as a convenient, schema-stable target model --
        the mechanism under test doesn't care what model a definition
        targets."""
        group_ref = f'order-bridge-test-{label}'
        return {
            'qualifying_lines': lambda: host,  # any non-empty recordset is a valid "there's something to sync" signal
            'group_lines': lambda lines: [group_ref],
            'find_existing': lambda group: self.Partner.search([('ref', '=', group)], limit=1),
            'vals': lambda group, existing: {'name': group, 'ref': group},
            'record_model': lambda: 'res.partner',
            'link': lambda group, record: None,
        }

    def test_default_definitions_is_empty(self):
        host = self.Host.create({})
        self.assertEqual(host._bridge_definitions(), [])
        self.assertEqual(host._bridge_sync(), [])

    def test_bridge_sync_runs_every_registered_definition(self):
        """The exact case that broke dispatch.mixin: two definitions
        registered on the same host must BOTH run when _bridge_sync() is
        called, not just whichever one happened to be registered last."""
        host = self.Host.create({})
        definitions = [self._definition(host, 'freight'), self._definition(host, 'trading')]
        with patch.object(type(host), '_bridge_definitions', return_value=definitions):
            results = host._bridge_sync()

        self.assertEqual(len(results), 2)
        created_refs = {record.ref for _group, record, _was_created in results}
        self.assertEqual(created_refs, {'order-bridge-test-freight', 'order-bridge-test-trading'})
        self.assertTrue(all(was_created for _g, _r, was_created in results))

    def test_bridge_run_definition_updates_an_existing_record_instead_of_duplicating(self):
        host = self.Host.create({})
        definition = self._definition(host, 'freight')

        first_pass = host._bridge_run_definition(definition)
        self.assertEqual(len(first_pass), 1)
        _group, record, was_created = first_pass[0]
        self.assertTrue(was_created)

        second_pass = host._bridge_run_definition(definition)
        self.assertEqual(len(second_pass), 1)
        _group2, record2, was_created2 = second_pass[0]
        self.assertFalse(was_created2)
        self.assertEqual(record2, record)
        self.assertEqual(self.Partner.search_count([('ref', '=', 'order-bridge-test-freight')]), 1)

    def test_bridge_create_returning_empty_recordset_skips_the_group_silently(self):
        """A definition's own `create` can signal "skip this group" (e.g. a
        caught error) by returning an empty recordset -- _bridge_sync() must
        not treat that as a crash, and must not call `link` for it."""
        host = self.Host.create({})
        definition = self._definition(host, 'freight')
        definition['create'] = lambda vals: self.Partner.browse()

        linked = []
        definition['link'] = lambda group, record: linked.append(group)

        results = host._bridge_run_definition(definition)
        self.assertEqual(results, [])
        self.assertEqual(linked, [])
