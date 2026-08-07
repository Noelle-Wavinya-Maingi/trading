from odoo import models, fields, api


class OmniProductTemplate(models.Model):
    """
    This is a custom product template that is used to create an Omnifreight service product.
    The product can be used as a component in the manufacturing module but it does not cause stock movements
    """

    _inherit = 'product.template'

    ## Safely add a new product type to the product template
    type = fields.Selection(
        selection_add=[
            ('omni_service', 'Omnifreight Service'),
        ],
        ondelete={'omni_service': 'set default'},
    )

    ## Explicit service scope, so a service BOM does not have to be inferred from
    ## the product's name. Name inference remains as a fallback when this is unset
    ## (see omni_bom.py), which keeps existing products working unchanged.
    omni_service_scope = fields.Selection([
        ('fob', 'FOB'),
        ('freight', 'Freight'),
        ('lod', 'Destination'),
        ('fob_freight', 'FOB + Freight'),
        ('freight_lod', 'Freight + Destination'),
        ('fob_lod', 'FOB + Destination'),
        ('fob_freight_lod', 'FOB + Freight + Destination'),
    ], string='Service Scope',
        help="Service scope applied to BOMs built from this product. Leave empty to "
             "infer it from the product name (legacy behaviour, matched on the words "
             "FOB / Freight / Destination / LOD).")


    ## Ensure omni_service products are treated as consumable and phantom for BOM usage
    @api.onchange('type')
    def _onchange_type_set_properties(self):
        """
        Automatically sets properties for omni_service products:
        - Sets as phantom product (no stock moves)
        - Sets the configured freight service category
        - Enables MTO with manufacturing route for smart button
        """
        if self.type == 'omni_service':
            # Company-configured category, falling back to a name lookup
            category = self.env.company._omni_get_service_category()
            if category:
                self.categ_id = category.id
            
            # Ensure it's not tracked for inventory
            self.tracking = 'none'
            
            # Set as a service product (no stock moves)
            self.service_type = 'manual'
            
 

