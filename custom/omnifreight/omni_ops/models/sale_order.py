# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    """Extends sale.order to add freight file creation on confirm and to expose omni.ops.file records linked to this order. The freight file creation
    is done via the dispatch.mixin, which allows for a flexible and extensible way to define how records are created or updated based on the order's lines."""
    _name = 'sale.order'
    _inherit = ['sale.order', 'dispatch.mixin']

    omni_ops_file_ids = fields.Many2many('omni.ops.file', compute='_compute_omni_ops_file_ids')
    omni_ops_file_count = fields.Integer(compute='_compute_omni_ops_file_ids')

    @api.depends('order_line')
    def _compute_omni_ops_file_ids(self):
        for order in self:
            files = self.env['omni.ops.file'].search([('sale_line_id', 'in', order.order_line.ids)])
            order.omni_ops_file_ids = files
            order.omni_ops_file_count = len(files)

    def action_view_omni_ops_files(self):
        self.ensure_one()
        action = {
            'name': _('Freight Files'),
            'type': 'ir.actions.act_window',
            'res_model': 'omni.ops.file',
            'context': {'default_sale_line_id': self.order_line[:1].id},
        }
        if len(self.omni_ops_file_ids) == 1:
            action.update(view_mode='form', res_id=self.omni_ops_file_ids.id)
        else:
            action.update(view_mode='list,form', domain=[('id', 'in', self.omni_ops_file_ids.ids)])
        return action

    # === freight file creation on confirm ===

    def _action_confirm(self):
        result = super()._action_confirm()
        for order in self:
            if order.quote_type and order.order_line:
                order._bridge_run_definition(order._freight_bridge_definition())
        return result

    def _map_quote_type_to_service_scope(self, quote_type):
        """Map quote_type to service_scope for BOM lookup."""
        mapping = {
            'fob_only': 'fob',
            'fob_freight': 'fob_freight',
            'freight_only': 'freight',
            'lod_only': 'lod',
            'fob_freight_lod': 'fob_freight_lod',
            'freight_dap': 'freight_lod',
        }
        return mapping.get(quote_type, quote_type)

    def _get_step_template_for_service_scope(self, quote_type):
        """Retrieve the appropriate step template based on the quote_type."""
        if 'omni.service.step.template' not in self.env:
            raise UserError("Freight step templates require the freight operations module.")

        service_scope = self._map_quote_type_to_service_scope(quote_type)

        template = self.env['omni.service.step.template'].search([
            ('service_scope', '=', service_scope),
        ], limit=1)

        if not template:
            raise UserError(
                f"No step template found for service scope '{service_scope}'. "
                "Please create one."
            )

        return template

    # === dispatch.mixin registration ===
    def _bridge_definitions(self):
        return super()._bridge_definitions() + [self._freight_bridge_definition()]

    def _freight_bridge_definition(self):
        """Define the bridge for creating or updating freight files based on the sale order's lines. This definition specifies how
        to filter qualifying lines, group them, find existing records, prepare values for creation or update, and link the resulting record back to the order."""
        return {
            'qualifying_lines': self._freight_bridge_qualifying_lines,
            'group_lines': self._freight_bridge_group_lines,
            'find_existing': self._freight_bridge_find_existing,
            'vals': self._freight_bridge_vals,
            'record_model': self._freight_bridge_record_model,
            'create': self._freight_bridge_create,
            'link': self._freight_bridge_link,
        }

    def _freight_bridge_qualifying_lines(self):
        self.ensure_one()

        freight_product = self.env['product.product'].search([
            ('name', '=', 'Freight Forwarding Service')
        ], limit=1)
        if not freight_product:
            return self.env['sale.order.line']

        # Check if a step template exists for the quote_type, if not, log a warning and post a message to the order's chatter, then return an empty recordset to prevent file creation.
        try:
            self._get_step_template_for_service_scope(self.quote_type)
        except UserError as exc:
            _logger.warning(
                "No freight step template for order %s (quote_type=%s): %s",
                self.name, self.quote_type, exc,
            )
            self.message_post(body=(
                "No freight step template found for this quotation's service "
                "scope, so no freight file was created. Configure one under "
                "Operations > Configuration > Freight Step Templates."
            ))
            return self.env['sale.order.line']

        return self.order_line.filtered(
            lambda l: l.product_id == freight_product and l.product_uom_qty > 0
        )

    def _freight_bridge_group_lines(self, lines):
        return [line for line in lines]

    def _freight_bridge_record_model(self):
        return 'omni.ops.file'

    def _freight_bridge_find_existing(self, group):
        """The dedup guard that didn't exist before the dispatch
        migration -- every confirm used to create a fresh record regardless
        of whether this line already had one."""
        return self.env['omni.ops.file'].search([('sale_line_id', '=', group.id)], limit=1)

    def _freight_bridge_vals(self, group, existing):
        if existing:
            # Nothing to update -- the fix is "don't duplicate", not "keep
            # re-syncing an existing file's fields", which was never part of
            # the original design (it only ever created, never updated).
            return {}

        line = group
        return {
            'product_id': line.product_id.id,
            'product_qty': line.product_uom_qty,
            'product_uom_id': line.product_uom_id.id,
            'origin': self.name,
            'sale_line_id': line.id,
            'company_id': self.company_id.id,
        }

    def _freight_bridge_create(self, vals):
        file = self._bridge_default_create('omni.ops.file', vals)
        template = self._get_step_template_for_service_scope(self.quote_type)
        template.generate_steps(file)
        return file

    def _freight_bridge_link(self, group, record):
        record.sale_line_id = group.id
