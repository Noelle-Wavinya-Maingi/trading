from odoo import fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    
    # module_ prefix is Odoo's own convention: ticking this box installs
    # whatever module is named after the suffix -- must match the module's
    # actual technical name (ele_trading_budget), not its pre-rename one.
    module_ele_trading_budget = fields.Boolean(string="Budgets")