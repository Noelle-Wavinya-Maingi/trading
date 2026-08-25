# -*- coding: utf-8 -*-
from odoo import models


class OrderBridgeMixin(models.AbstractModel):
    """Template for "confirm an order -> derive an industry operational
    record" flows (trading.trade from sale/purchase orders, mrp.production
    from freight quotations). Shares the four-step skeleton -- filter,
    group, create-or-update, link -- since that shape is identical across
    every known use; every step's actual behavior is supplied by the
    including model's overrides, since the concrete grouping, field
    mapping, and update strategy genuinely differ per vertical."""
    _name = 'order.bridge.mixin'
    _description = 'Order Bridge Mixin'

    def _bridge_definitions(self):
        """Return a list of bridge definitions for each bridge record type."""
        return []

    def _bridge_default_create(self, record_model, vals):
        """Default bridge record creation method. This can be overridden in specific models if needed."""
        return self.env[record_model].create(vals)

    def _bridge_run_definition(self, definition):
        """Run a single bridge definition on this record and return the results. This method handles the filtering, grouping,
        creation/updating, and linking of records based on the provided definition."""
        results = []
        lines = definition['qualifying_lines']()
        if not lines:
            return results
        for group in definition['group_lines'](lines):
            existing = definition['find_existing'](group)
            was_created = not existing
            vals = definition['vals'](group, existing)
            if existing:
                existing.write(vals)
                record = existing
            else:
                create = definition.get('create')
                record = (
                    create(vals) if create
                    else self._bridge_default_create(definition['record_model'](), vals)
                )
                if not record:
                    continue
            definition['link'](group, record)
            results.append((group, record, was_created))
        return results

    def _bridge_sync(self):
        """Run all bridge definitions on this record and return the results. This method iterates through all bridge definitions
        and applies them to the current record, collecting the results of each definition."""
        results = []
        for definition in self._bridge_definitions():
            results += self._bridge_run_definition(definition)
        return results
