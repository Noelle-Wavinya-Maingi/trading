# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class OmniOpsFile(models.Model):
    """Model representing a freight file in the Omni Freight System. This model serves as the central entity for managing freight
    operations, including associated steps, documents, and additional operations. It is linked to a product and can be associated with
    a sale order line for traceability. The model also computes various service flags and shipment details based on the associated."""
    _name = 'omni.ops.file'
    _description = 'Freight File'
    _inherit = ['process.bridge.mixin', 'mail.thread']
    _order = 'id desc'

    name = fields.Char(compute='_compute_name', store=True)
    origin = fields.Char(string='Source Document')
    # The product and quantity being shipped. These are used to generate the operational steps, and also to link the freight file to a sale order line if applicable.
    product_id = fields.Many2one('product.product', string='Product', required=True)
    product_qty = fields.Float(string='Quantity', default=1.0)
    product_uom_id = fields.Many2one('uom.uom', string='Unit of Measure')
    # The sale order line that this freight file is linked to, if any. This is used to link the freight file to the sale order and to generate the operational steps.
    sale_line_id = fields.Many2one('sale.order.line', string='Sale Order Line', index=True)
    sale_order_id = fields.Many2one(
        'sale.order', string='Sale Order', related='sale_line_id.order_id', store=True,
    )
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    step_ids = fields.One2many('omni.ops.step', 'file_id', string='Steps')
    fob_step_ids = fields.One2many(
        'omni.ops.step', 'file_id', string='FOB Steps',
        domain=[('service_type', '=', 'fob')],
    )
    freight_step_ids = fields.One2many(
        'omni.ops.step', 'file_id', string='Freight Steps',
        domain=[('service_type', '=', 'freight')],
    )
    lod_step_ids = fields.One2many(
        'omni.ops.step', 'file_id', string='Destination Steps',
        domain=[('service_type', '=', 'lod')],
    )
    document_ids = fields.One2many('omnifreight.documents', 'file_id', string='Documents')
    additional_operations_ids = fields.One2many(
        'additional.file.operations', 'file_id', string='Additional Operations',
        help="Additional operations specific to this freight file",
    )

    has_fob_service = fields.Boolean(string='Has FOB Service', compute='_compute_service_flags', store=True)
    has_freight_service = fields.Boolean(string='Has Freight Service', compute='_compute_service_flags', store=True)
    has_lod_service = fields.Boolean(string='Has LOD Service', compute='_compute_service_flags', store=True)

    # === SHIPMENT / QUOTATION-DERIVED FIELDS ===
    quote_type = fields.Selection(related='sale_line_id.order_id.quote_type', string='Quote Type', store=True)
    route_id = fields.Many2one('omnifreight.route', string='Route', compute='_compute_sale_fields', store=True)
    partner_id = fields.Many2one('res.partner', string='Customer', compute='_compute_sale_fields', store=True)
    freight_carrier_id = fields.Many2one('res.partner', string='Carrier')
    buyer_id = fields.Many2one('res.partner', string='Buyer/ Consignee')
    seller_id = fields.Many2one('res.partner', string='Seller/ Shipper')
    incoterm_to = fields.Many2one(related='sale_line_id.order_id.incoterm_to_id', string='Incoterms To', store=True)
    incoterm_from = fields.Many2one(related='sale_line_id.order_id.incoterm_id', string='Incoterms From', store=True)
    transporter_id = fields.Many2one('res.partner', string='Haulier', compute='_compute_sale_fields', store=True)
    city_from = fields.Many2one('unloc.city', string='City From', compute='_compute_sale_fields', store=True)
    city_to = fields.Many2one('unloc.city', string='City To', compute='_compute_sale_fields', store=True)
    supplier_id = fields.Many2one('res.partner', string='Transporter', compute='_compute_sale_fields', store=True)

    # Package Details
    package_details = fields.Many2one('omnifreight.package.details', string='Package Details', compute='_compute_sale_fields', store=True)
    container_type = fields.Selection(related='package_details.container_type', string='Container Type', store=True)
    contents = fields.Many2many(related='package_details.contents', string='Contents')
    content_classification = fields.Selection(related='package_details.content_classification', string='Content Classification', store=True)
    soc = fields.Boolean(related='package_details.soc', string='SOC', store=True)
    weight = fields.Float(related='package_details.weight', string='Weight', store=True, readonly=False)
    volume = fields.Float(related='package_details.volume', string='Volume', store=True, readonly=False)

    # Shipment fields
    pol = fields.Char(string='POL', compute='_compute_port_fields', store=True)
    pod = fields.Char(string='POD', compute='_compute_port_fields', store=True)

    # Operations fields
    booking_ref = fields.Char(string='Booking Reference')
    carrier_agent_id = fields.Many2one('res.partner', string='Carrier Agent', compute='_compute_carrier_agent_id', store=True)
    vessel_id = fields.Many2one('freight.vessel', string='Vessel')
    etd = fields.Datetime(string='ETD')
    eta = fields.Datetime(string='ETA')

    @api.depends('origin')
    def _compute_name(self):
        """Compute the name of the freight file based on the sequence and origin."""
        for file in self:
            if not file.name or file.name == _('New'):
                file.name = self.env['ir.sequence'].next_by_code('omni.ops.file') or _('New')

    def action_view_sale_order(self):
        self.ensure_one()
        return {
            'name': _('Sale Order'),
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'view_mode': 'form',
            'res_id': self.sale_order_id.id,
        }

    @api.depends('step_ids.service_type')
    def _compute_service_flags(self):
        """Set the service flags based on the service types of the operational steps."""
        for file in self:
            service_types = set(file.step_ids.mapped('service_type'))
            file.has_fob_service = 'fob' in service_types
            file.has_freight_service = 'freight' in service_types
            file.has_lod_service = 'lod' in service_types

    @api.depends('sale_line_id')
    def _compute_carrier_agent_id(self):
        """Compute carrier_agent_id from carrier_id in connected sale order."""
        for file in self:
            order = file.sale_line_id.order_id if file.sale_line_id else None
            file.carrier_agent_id = getattr(order, 'freight_carrier_id', False) if order else False

    @api.depends('sale_line_id')
    def _compute_sale_fields(self):
        """Compute fields from connected sale order."""
        for file in self:
            order = file.sale_line_id.order_id if file.sale_line_id else None
            if order:
                file.route_id = order.route_id
                file.partner_id = order.partner_id
                file.package_details = order.package_details_id
                file.city_to = order.lod_service_city
                file.city_from = order.city_id
                file.supplier_id = order.selected_lod_transport_rate_id.supplier_id
                selected_fob_rate = order.rate_link_ids.filtered(lambda r: r.is_selected_fob)
                if selected_fob_rate:
                    file.transporter_id = selected_fob_rate[0].rate_id.supplier_id

    @api.depends('route_id', 'sale_line_id.order_id.port_of_loading', 'sale_line_id.order_id.port_of_dispatch',
                 'has_fob_service', 'has_lod_service', 'quote_type')
    def _compute_port_fields(self):
        """Compute port fields from route or individual ports based on service scope."""
        for file in self:
            if file.route_id:
                # Multi-port scenario: use route ports
                file.pol = file.route_id.departure_port_id.name
                file.pod = file.route_id.arrival_port_id.name
                continue

            # Single-port scenarios: determine based on the file's own
            # generated steps (has_fob_service/has_lod_service), falling
            # back to quote_type if steps haven't been generated yet.
            order = file.sale_line_id.order_id if file.sale_line_id else None
            if not order:
                file.pol = False
                file.pod = False
                continue

            is_fob = file.has_fob_service or file.quote_type in ('fob_only', 'fob')
            is_lod = file.has_lod_service or file.quote_type in ('lod_only', 'lod')
            if is_fob and not is_lod:
                file.pol = order.port_of_loading.name if order.port_of_loading else False
                file.pod = False
            elif is_lod and not is_fob:
                file.pol = False
                file.pod = order.port_of_dispatch.name if order.port_of_dispatch else False
            else:
                file.pol = False
                file.pod = False

    @api.onchange('product_id')
    def _onchange_product_id(self):
        """Set product_uom_id and product_qty when product_id is changed, for service products."""
        if self.product_id and self.product_id.type == 'omni_service':
            self.product_uom_id = self.product_id.uom_id
            self.product_qty = 1.0

    def write(self, vals):
        """Override write to track document changes and attach files to chatter."""
        original_states = self._get_original_document_states()

        result = super().write(vals)

        if 'document_ids' in vals:
            self._process_document_changes(original_states)

        return result

    def _get_original_document_states(self):
        """Get the original state of documents before write operation."""
        original_states = {}
        for file in self:
            original_states[file.id] = {
                'document_ids': file.document_ids.ids,
                'document_names': {doc.id: doc.filename for doc in file.document_ids}
            }
        return original_states

    def _process_document_changes(self, original_states):
        """Process document additions and removals after write operation."""
        for file in self:
            original_data = original_states.get(file.id, {})
            current_docs = file.document_ids

            new_docs, removed_doc_data = self._find_document_changes(original_data, current_docs)

            if new_docs:
                self._handle_new_documents(file, new_docs)

            if removed_doc_data:
                self._handle_removed_documents(file, removed_doc_data)

    def _find_document_changes(self, original_data, current_docs):
        """Identify newly added and removed documents."""
        original_ids = set(original_data.get('document_ids', []))
        current_ids = set(current_docs.ids)

        new_doc_ids = current_ids - original_ids
        new_docs = current_docs.filtered(lambda doc: doc.id in new_doc_ids)

        removed_doc_ids = original_ids - current_ids
        removed_filenames = [
            filename for doc_id, filename in original_data.get('document_names', {}).items()
            if doc_id in removed_doc_ids and filename
        ]

        return new_docs, removed_filenames

    def _handle_new_documents(self, file, new_docs):
        """Handle newly added documents by creating attachments and posting messages."""
        valid_docs = new_docs.filtered(lambda doc: doc.document_upload and doc.filename)

        if not valid_docs:
            return

        attachments = []
        document_names = []

        for document in valid_docs:
            attachment = self._create_chatter_attachment(file, document)
            attachments.append(attachment.id)
            document_names.append(document.filename)

        if document_names:
            self._post_addition_message(file, document_names, attachments)

    def _handle_removed_documents(self, file, removed_filenames):
        """Handle removed documents by deleting attachments."""
        if removed_filenames:
            self._remove_chatter_attachments(file, removed_filenames)

    def _create_chatter_attachment(self, file, document):
        """Create a chatter attachment for a document."""
        return self.env['ir.attachment'].create({
            'name': document.filename,
            'datas': document.document_upload,
            'res_model': 'omni.ops.file',
            'res_id': file.id,
            'type': 'binary',
        })

    def _post_addition_message(self, file, document_names, attachments):
        """Post notifications about document additions to chatter."""
        document_list = "\n".join([f"- {name}" for name in document_names])

        file.message_post(
            body=_("The following document(s) were added:\n%s") % document_list,
            message_type="notification",
        )

    def _remove_chatter_attachments(self, file, filenames):
        """Remove chatter attachments for deleted documents."""
        attachments = self.env['ir.attachment'].search([
            ('res_model', '=', 'omni.ops.file'),
            ('res_id', '=', file.id),
            ('name', 'in', filenames)
        ])
        attachments.unlink()
