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

    def _bridge_qualifying_lines(self):
        """Return the order_lines that should feed an operational record."""
        raise NotImplementedError

    def _bridge_group_lines(self, lines):
        """Group qualifying lines into one operational record each (e.g.
        one aggregate group for the whole order, or one group per line)."""
        raise NotImplementedError

    def _bridge_find_existing(self, group):
        """Return the already-linked record for this group, or an empty
        recordset if none. Defaults to "always create" -- override to opt
        into create-or-update once a link field exists to check."""
        return self.env[self._bridge_record_model()]

    def _bridge_vals(self, group, existing):
        """Map a line-group to create()/write() vals for the target model.
        `existing` (the same recordset _bridge_find_existing returned for
        this group -- empty if none) is passed in rather than re-checked,
        since create-vals and update-vals commonly need different shapes
        (e.g. a full payload with defaults vs. a diff of only changed
        fields) and re-deriving "is this a create or an update" separately
        here would just duplicate _bridge_sync's own check."""
        raise NotImplementedError

    def _bridge_record_model(self):
        """Technical name of the operational model (e.g. 'trading.trade')."""
        raise NotImplementedError

    def _bridge_link(self, group, record):
        """Persist the link from this group back to the created/updated
        record (on self, on a line, wherever the vertical stores it)."""
        raise NotImplementedError

    def _bridge_create(self, vals):
        """Create the target record from vals. Default: plain create().
        Override only if a vertical needs custom error handling around
        creation (e.g. catch-and-log instead of letting an exception abort
        the whole confirm); return an empty recordset for the target model
        to signal "skip this group" -- _bridge_sync will then skip linking
        and omit it from the returned results, the same as if it had never
        qualified."""
        return self.env[self._bridge_record_model()].create(vals)

    def _bridge_sync(self):
        """Run the shared skeleton: call after super() in whichever
        confirm-hook (action_confirm/_action_confirm/button_confirm) the
        including model overrides. Returns a list of (group, record,
        was_created) so the caller can run its own side effects (activity
        scheduling, recomputes) per group without the mixin needing to know
        about any of that -- those stay vertical-specific, not shared."""
        lines = self._bridge_qualifying_lines()
        if not lines:
            return []
        results = []
        for group in self._bridge_group_lines(lines):
            existing = self._bridge_find_existing(group)
            was_created = not existing
            vals = self._bridge_vals(group, existing)
            if existing:
                existing.write(vals)
                record = existing
            else:
                record = self._bridge_create(vals)
                if not record:
                    continue
            self._bridge_link(group, record)
            results.append((group, record, was_created))
        return results
