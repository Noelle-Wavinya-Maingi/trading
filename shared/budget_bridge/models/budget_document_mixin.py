# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class BudgetDocumentMixin(models.AbstractModel):
    """Mixin for models that are budget documents (headers)."""
    _name = 'budget.document.mixin'
    _description = 'Budget Document Mixin'

    name = fields.Char(
        'Budget Reference',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New'),
        index=True,
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        required=True,
        default=lambda self: self.env.company.currency_id,
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('closed', 'Closed'),
    ], string='Status', default='draft', tracking=True, required=True)

    def _budget_sequence_code(self):
        """Return the sequence code to use for generating budget reference numbers. Must be overridden in the including model."""
        raise NotImplementedError

    @api.model_create_multi
    def create(self, vals_list):
        """Generate budget reference number (batch-safe)."""
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    self._budget_sequence_code()
                ) or _('New')
        return super().create(vals_list)

    def action_confirm(self):
        """Confirm the budget."""
        self.ensure_one()
        self.write({'state': 'confirmed'})

    def action_close(self):
        """Close the budget."""
        self.ensure_one()
        self.write({'state': 'closed'})
