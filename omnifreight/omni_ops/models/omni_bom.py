from odoo import api, fields, models, _
from collections import defaultdict
from datetime import datetime
import re
from odoo.exceptions import UserError, ValidationError
from .mixins.service_scope_mixin import ServiceScopeMixin
from .mixins.bom_utilities_mixin import BomUtilitiesMixin


class OmniMrpBom(models.Model, ServiceScopeMixin, BomUtilitiesMixin):
    _inherit = 'mrp.bom'
    
    # === FIELDS ===
    # Extend product domain to include Omnifreight services
    product_tmpl_id = fields.Many2one(
        'product.template', 'Product',
        check_company=True, index=True,
        domain="[('type', 'in', ('consu','product','omni_service'))]",
    )

    product_id = fields.Many2one(
        'product.product', 'Product Variant',
        check_company=True, index=True,
        domain="['&', ('product_tmpl_id', '=', product_tmpl_id), ('type', 'in', ('consu','product','omni_service'))]",
        help="If a product variant is defined the BOM is available only for this product."
    )

    # Service BOM type for freight forwarding operations
    type = fields.Selection(
        selection_add=[('service', 'Service Operations Only')],
        ondelete={'service': 'cascade'}
    )

    # === DEFAULT METHODS ===
    @api.model
    def default_get(self, fields_list):
        """Set default type to 'service' for new BOMs."""
        res = super().default_get(fields_list)
        if 'type' in fields_list and 'type' not in res:
            res['type'] = 'service'
        return res

    @api.model
    def _infer_service_scope_from_name(self, product_name):
        """Guess a service scope from words in the product's name.

        Legacy fallback only, used when the product carries no explicit
        omni_service_scope. It is deliberately kept so existing products keep
        working, but it is English- and naming-convention-dependent: setting
        the scope on the product is what makes this deterministic. Returns
        False when nothing matches.

        Note the asymmetry preserved from the original implementation: the
        combined scopes below match only on the word 'destination', while a bare
        'lod' maps to the LOD scope. So a product named "FOB LOD" infers 'fob',
        not 'fob_lod'. That is almost certainly unintended, but changing it would
        silently reassign the scope -- and therefore the loaded operations -- of
        existing BOMs, so it is left as-is; set omni_service_scope on the product
        to get the right answer."""
        if not product_name:
            return False
        name = product_name.lower()
        has_fob = 'fob' in name
        has_freight = 'freight' in name
        has_destination = 'destination' in name

        if has_fob and has_freight and has_destination:
            return 'fob_freight_lod'
        if has_fob and has_freight:
            return 'fob_freight'
        if has_freight and has_destination:
            return 'freight_lod'
        if has_fob and has_destination:
            return 'fob_lod'
        if has_fob:
            return 'fob'
        if has_freight:
            return 'freight'
        if has_destination or 'lod' in name:
            return 'lod'
        return False

    # === ONCHANGE METHODS ===
    @api.onchange('product_tmpl_id')
    def onchange_product_tmpl_id(self):
        """Auto-detect Omnifreight service products and set BOM type."""
        # Call super to get base behavior (UoM updates, etc.)
        result = super().onchange_product_tmpl_id()
        
        if self.product_tmpl_id:
            # For service BOMs, prevent default code generation and use our naming convention
            if self.type == 'service' or (self.product_tmpl_id.type == 'omni_service'):
                # Auto-set to service BOM type for Omnifreight services
                self.type = 'service'
                
                # Clear any code that was set by base method - we'll generate our own
                if self.code and '(new)' in self.code:
                    self.code = False
                
                # Prefer the scope set explicitly on the product; only guess from
                # the product's name when it has none.
                self.service_scope = (
                    self.product_tmpl_id.omni_service_scope
                    or self._infer_service_scope_from_name(self.product_tmpl_id.name)
                    or self.service_scope
                )


                # Generate code if service_scope is set
                if self.service_scope and not self.code:
                    self._generate_code()
        
        return result
    
    @api.onchange('service_scope')
    def _onchange_service_scope(self):
        """Generate code when service_scope changes."""
        if self.type == 'service' and self.service_scope and not self.code:
            self._generate_code()
        # Also call the mixin's onchange if it exists
        if hasattr(super(), '_onchange_service_scope'):
            return super()._onchange_service_scope()
    
    def _generate_code(self):
        """Generate code with naming convention: OPS -Service Scope - month - number"""
        if not self.service_scope:
            return
        
        # Get the display name for service scope
        service_scope_field = self._fields.get('service_scope')
        if service_scope_field and hasattr(service_scope_field, 'selection'):
            selection = service_scope_field.selection
            if callable(selection):
                selection = selection(self.env)
            scope_display = dict(selection).get(self.service_scope, self.service_scope)
        else:
            scope_display = self.service_scope
        
        # Get current month (01-12)
        month = datetime.now().strftime('%m')
        
        # Generate sequence number (find existing codes with same prefix)
        prefix = f"OPS -{scope_display} -{month} -"
        domain = [('code', '=like', f'{prefix}%')]
        if self.id and self.id.origin:
            domain.append(('id', '!=', self.id.origin))
        existing_codes = self.search(domain).mapped('code')
        
        # Extract numbers from existing codes and find next number
        numbers = []
        for code in existing_codes:
            match = re.search(rf'{re.escape(prefix)}(\d+)', code)
            if match:
                numbers.append(int(match.group(1)))
        
        next_number = max(numbers) + 1 if numbers else 1
        self.code = f"{prefix}{next_number:03d}"

    # === CRUD METHODS ===
    @api.model_create_multi
    def create(self, vals_list):
        """Override create to generate code/reference with naming convention: OPS -Service Scope - month - number"""
        records = super().create(vals_list)
        
        # Generate code after creation if service_scope is set and code wasn't set (or was default)
        for record in records:
            if record.type == 'service' and record.service_scope:
                # Clear default code if it matches the pattern from base onchange
                if record.code and '(new)' in record.code:
                    record.code = False
                # Generate our custom code
                if not record.code:
                    record._generate_code()
        
        return records
    
    def write(self, vals):
        """Update code when service_scope changes if code follows the naming convention"""
        result = super().write(vals)
        
        # If service_scope is being updated, regenerate code if it follows our convention
        if 'service_scope' in vals:
            for record in self:
                if record.type == 'service' and record.service_scope:
                    # Check if current code follows our pattern or is default
                    current_code = record.code or ''
                    pattern_match = re.match(r'OPS -(.+?) -\d{2} -\d+', current_code)
                    
                    # If it doesn't follow our pattern or is empty/default, regenerate
                    if not pattern_match or not current_code or '(new)' in current_code:
                        record._generate_code()
        
        return result

    # === BUSINESS METHODS ===
    @api.model
    def _bom_find(self, products, picking_type=None, company_id=False, bom_type=False):
        """Override to allow omni_service products to find BOMs."""
        bom_by_product = defaultdict(lambda: self.env['mrp.bom'])
        # Allow omni_service products to find BOMs (don't filter them out)
        products = products.filtered(lambda p: p.type != 'service' or p.type == 'omni_service')
        if not products:
            return bom_by_product
        domain = self._bom_find_domain(products, picking_type=picking_type, company_id=company_id, bom_type=bom_type)

        # Performance optimization, allow usage of limit and avoid the for loop `bom.product_tmpl_id.product_variant_ids`
        if len(products) == 1:
            bom = self.search(domain, order='sequence, product_id, id', limit=1)
            if bom:
                bom_by_product[products] = bom
            return bom_by_product

        boms = self.search(domain, order='sequence, product_id, id')

        products_ids = set(products.ids)
        for bom in boms:
            products_implies = bom.product_tmpl_id.product_variant_ids
            if bom.product_id:
                products_implies = products_implies & bom.product_id
            for product in products_implies:
                if product.id in products_ids:
                    bom_by_product[product] = bom
        return bom_by_product
