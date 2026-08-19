from odoo import models, fields, api

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'
    
    ele_trade_id = fields.Many2one('trading.trade', string='Trade', help='Related trade for this move line')
    
    @api.model_create_multi
    def create(self, vals_list):
        """Ensure invoice lines from sale orders inherit trade information"""
        for vals in vals_list:
            if vals.get('move_id'):
                move = self.env['account.move'].browse(vals['move_id'])
                if move and move.ele_is_from_sale_order and move.ele_trade_id and not vals.get('ele_trade_id'):
                    # If the invoice line doesn't have a trade but the parent invoice does, propagate the trade to the line
                    vals['ele_trade_id'] = move.ele_trade_id.id
                if move and move.ele_is_from_purchase_order and move.ele_trade_id and not vals.get('ele_trade_id'):
                    vals['ele_trade_id'] = move.ele_trade_id.id
        
        return super().create(vals_list)
    
    @api.onchange('product_id')
    def _onchange_product_id_trade_domain(self):
        # Narrow the trade picker to trades on the same product, so nobody
        # links an invoice line to a trade for a different commodity.
        if self.product_id:
            return {
                'domain': {
                    'ele_trade_id': [('product_id', '=', self.product_id.id)]
                }
            }
            
    @api.onchange('ele_trade_id')
    def _onchange_trade_id(self):
        """On change of ele_trade_id, check the header"""
        for line in self:
            if line.ele_trade_id:
                line.move_id.ele_trade_id = line.ele_trade_id
                line.move_id._compute_is_from_order()
    