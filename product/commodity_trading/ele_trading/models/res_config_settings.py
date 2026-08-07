from odoo import fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    
    # module_ prefix is Odoo's own convention: ticking this box installs
    # trading_budget, it isn't just a config flag.
    module_trading_budget = fields.Boolean(string="Budgets")