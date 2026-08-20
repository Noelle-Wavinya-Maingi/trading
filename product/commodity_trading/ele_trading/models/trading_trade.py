import logging

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

class TradingTrade(models.Model):
    """Core model definition: fields, sequencing, ele_status workflow."""
    _name = 'trading.trade'
    _description = 'Trading Trade'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'process.bridge.mixin']

    name = fields.Char(
        string="Trade Name",
        required=True,
        copy=False,
        default="New",
        readonly=True,
    )

    ele_trade_type = fields.Selection(
        [('short', 'Short'), ('long', 'Long')],
        string="Trade Type",
        required=True
    )

    # Many2many to support multiple lots with quantity tracking
    ele_lot_ids = fields.Many2many(
        'stock.lot',
        string="Lots",
        help="Lots associated with this trade (automatically set when receiving goods)"
    )
    
    # Track total quantity from all lots
    ele_total_lot_quantity = fields.Float(
        string='Total Lot Quantity',
        compute='_compute_total_lot_quantity',
        store=True,
        help='Total quantity from all linked lots'
    )

    # Purchase side fields (can be 0 if no purchase yet)
    quantity = fields.Float(string='Purchase Quantity', required=False, default=0.0)
    price = fields.Monetary(string='Purchase Price', required=False, currency_field='ele_purchase_currency_id')
    ele_purchase_currency_id = fields.Many2one('res.currency', string='Purchase Currency', default=lambda self: self.env.company.currency_id)
    ele_purchase_date = fields.Date(string='Purchase Date', default=fields.Date.context_today, help='Used to look up the FX rate when converting to reporting currency')
    
    # Sales side fields
    ele_sales_price = fields.Monetary(
        string="Sales Price",
        currency_field='ele_sale_currency_id',
        compute='_compute_sales_price_and_currency',
        store=True,
        readonly=False,
        help="Actual sale price per unit, in its original sale currency. "
             "Auto-filled from confirmed Sale Orders for long trades; "
             "editable manually otherwise (e.g. short trades)."
    )
    ele_sale_currency_id = fields.Many2one(
        'res.currency',
        string='Sale Currency',
        compute='_compute_sales_price_and_currency',
        store=True,
        readonly=False,
        default=lambda self: self.env.company.currency_id,
    )

    # ── Reporting currency — all P&L expressed in this ───────────────────
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id
    )

    # ── Converted prices in reporting currency ────────────────────────────
    ele_price_in_base_currency = fields.Monetary(
        string='Purchase Price (Reporting Currency)',
        compute='_compute_currency_conversions',
        store=True,
        currency_field='currency_id',
    )
    ele_sales_price_in_base_currency = fields.Monetary(
        string='Sales Price (Reporting Currency)',
        compute='_compute_currency_conversions',
        store=True,
        currency_field='currency_id',
    )

    # ── Company (needed for _convert()) ──────────────────────────────────
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
    )

    ele_status = fields.Selection(
        [('draft','Draft'),
         ('confirmed','Confirmed'),
         ('closed','Closed')],
        default='draft',
        tracking=True,
        group_expand='_group_expand_status'
    )
    
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        required=True,
        domain="[('product_tmpl_id.ele_is_tradeable', '=', True)]",
        help="Product associated with this trade"
    )
    
    # Sale Orders linked to this trade
    ele_sale_order_ids = fields.Many2many(
        'sale.order',
        string='Sale Orders',
        help="Sale orders that have sold from this trade"
    )
    
    # Purchase Order linked to this trade
    ele_purchase_id = fields.Many2one('purchase.order', string='Purchase Order', ondelete='set null')
    
    # NOTE: Monetary fields take their decimal precision from the linked
    # currency, not a 'digits' kwarg -- Float is the only field type that
    # accepts 'digits' directly. Passing it here is a no-op that Odoo 19
    # warns about on every load.
    ele_current_price = fields.Monetary(
        string='Current/Market Price',
        currency_field='ele_current_price_currency_id',
        help='Current market price for unrealized P&L calculation, in its own currency.',
        tracking=True
    )
    
    ele_current_price_currency_id = fields.Many2one(
        'res.currency',
        string="Market Price Currency",
        default=lambda self: self.env.company.currency_id
    )
    
    ele_current_price_in_base_currency = fields.Monetary(
        string="Current/Market Price (Reporting Currency)",
        compute="_compute_currency_conversions",
        store=True,
        currency_field='currency_id',
    )
    
    ele_additional_costs = fields.Float(
        string="Additional Costs",
        default = 0.0
    )
    
    ele_additional_revenue = fields.Float(
        string="Additional Revenue",
        default = 0.0
    )
    
    ele_invoice_ids = fields.One2many('account.move', 'ele_trade_id', string='Invoices')

    # NOTE: Trade Budgets (budget_ids, budget_id, budget_state,
    # action_create_budget, action_view_budget) are an OPTIONAL feature and
    # deliberately do NOT live here. Core trading has no dependency on
    # 'trading.trade.budget' at all -- that model, and every field/method
    # referencing it, lives in the separate 'ele_trading_budget' bridge module
    # (see trading_budget/models/trading_trade.py, an _inherit extension of
    # this same model), so that Trade Budgets can be installed/uninstalled
    # independently of Trading itself.
    #
    # ele_has_budget IS kept here, but as a plain non-computed field defaulting
    # to False -- this is a stub purely so that trading_trade_views.xml's
    # invisible="ele_has_budget" conditions (on cards that fall back to showing
    # unconditionally when no budget exists) always validate, even if
    # 'ele_trading_budget' is never installed. 'ele_trading_budget' overrides this
    # same field, turning it into a real compute based on budget_ids.
    ele_has_budget = fields.Boolean('Has Budget', default=False)

    # step_ids/has_steps (process.bridge.mixin) prove the generic process
    # engine's anchor mixin works for a zero-step consumer -- nothing here
    # creates a trading.trade.step today. Trading's own draft/confirmed/closed
    # `ele_status` lifecycle already covers what Trading needs; see
    # docs/PROCESS_ENGINE_MIGRATION_PLAN.md Phase 0.
    step_ids = fields.One2many('trading.trade.step', 'ele_trade_id', string='Steps')

    ele_product_uom = fields.Many2one(
        string="Unit of Measure",
        related="product_id.uom_id",
        store=False,
        readonly=True
    )

    # ═══════════════════ KANBAN/LIST GROUP ORDER ═════════════════════════
    @api.model
    def _group_expand_status(self, states, domain):
        """Force kanban/list group-by columns to follow the declared selection order (Draft, Confirmed, Closed) instead of the defaultalphabetical fallback ('closed' < 'confirmed' < 'draft')."""
        return [key for key, _label in self._fields['ele_status'].selection]

    # _group_by_full = {
    #     'ele_status': '_read_group_status_full',
    # }
    
    # @api.model
    # def _read_group_status_full(self, present_ids, domain, **kwargs):
    #     selection = self._fields['ele_status'].selection
    #     keys = [key for key, _label in selection]
    #     folded = {key: (key == 'draft') for key in keys}
    #     return keys, folded

    # ═══════════════════ CRUD / WORKFLOW ══════════════════════════════════
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                ele_trade_type = vals.get('ele_trade_type')
                if ele_trade_type == 'long':
                    seq_code = 'trading.trade.long'
                elif ele_trade_type == 'short':
                    seq_code = 'trading.trade.short'
                else:
                    seq_code = 'trading.trade.long'
                vals['name'] = self.env['ir.sequence'].next_by_code(seq_code) or 'New'

            # Ensure product_id is set
            if 'product_id' not in vals or not vals.get('product_id'):
                _logger.warning(f"Creating trade without product_id!")
                
        return super().create(vals_list)

    def action_confirm(self):
        """Open the trade for trading"""
        for trade in self:
            if trade.ele_status == 'draft':
                _logger.info(f"🌼 Confirming trade {trade.name}")
                trade.write({'ele_status': 'confirmed'})
                trade._compute_all_trade_fields()
        return True

    def write(self, vals):
        """Override write to trigger recomputation when needed"""
        result = super().write(vals)
        
        # Trigger recomputation if relevant fields changed
        if any(field in vals for field in ['quantity', 'price', 'ele_current_price', 'ele_lot_ids', 'ele_sale_order_ids', 'ele_purchase_id', 'ele_purchase_currency_id', 'ele_purchase_date',]):
            self._compute_all_trade_fields()
        
        return result

    def _sync_budget_line_for_move(self, move, field_name, amount):
        """No-op by default -- overridden by 'ele_trading_budget' if installed.

        account_move_lifecycle.py calls this unconditionally whenever a
        move's contribution to ele_additional_costs/ele_additional_revenue changes,
        regardless of whether the optional Trade Budget feature is present.
        Keeping a harmless no-op here means core Trading never breaks if
        'ele_trading_budget' isn't installed; the bridge module's _inherit
        override supplies the real budget-line-syncing behavior.
        """
        return

    def _remove_budget_line_for_move(self, move):
        """No-op by default -- overridden by 'ele_trading_budget' if installed.
        See _sync_budget_line_for_move for why this stub exists in core."""
        return

    def _compute_all_trade_fields(self):
        """Trigger recomputation of all computed fields."""
        for record in self:
            record._compute_sales_price_and_currency()
            record._compute_currency_conversions()
            record._compute_sales_totals()
            record._compute_position()
            record._compute_costs()
            record._compute_pnl()
            record._compute_performance()
            record._compute_on_hand_quantity()
            record._compute_total_lot_quantity()
            record._compute_invoice_count()