# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class BomUtilitiesMixin(models.AbstractModel):
    """Mixin for BOM utilities including field renaming and display name computation."""
    _name = 'omni.bom.utilities.mixin'
    _description = 'BOM Utilities Mixin'

    display_name = fields.Char(compute='_compute_display_name', store=True)

    @api.depends('service_scope', 'product_tmpl_id')
    def _compute_display_name(self):
        """Compute display name for process templates with service scope."""
        for record in self:
            if hasattr(record, 'type') and hasattr(record, 'service_scope'):
                if record.type == 'service' and record.service_scope and record.product_tmpl_id:
                    # Get service scope labels
                    scope_mapping = {
                        'fob': 'FOB',
                        'freight': 'Freight',
                        'lod': 'Destination',
                        'fob_freight': 'FOB, Freight',
                        'freight_lod': 'Freight, Destination',
                        'fob_lod': 'FOB, Destination',
                        'fob_freight_lod': 'FOB, Freight, Destination',
                    }
                    
                    scope_label = scope_mapping.get(record.service_scope, record.service_scope)
                    record.display_name = f"Template for {scope_label}"
                else:
                    # Use default display name for non-service records
                    if hasattr(super(), '_compute_display_name'):
                        super(BomUtilitiesMixin, record)._compute_display_name()
                    else:
                        record.display_name = record.name or record.id
            else:
                # Fallback for records without service scope
                record.display_name = record.name or record.id
