# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class OperationsBudgetLine(models.Model):
    """Shared budget line, reused across industries."""
    _name = 'operations.budget.line'
    _description = 'Budget Line'
    _order = 'sequence, id'
    _rec_name = 'name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # === BASIC FIELDS ===
    name = fields.Char('Description', required=True, tracking=True)
    sequence = fields.Integer('Sequence', default=10)
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        required=True,
        default=lambda self: self.env.company.currency_id
    )

    # === DISPLAY TYPE (section/note rows) ===
    display_type = fields.Selection([
        ('line_section', 'Section'),
        ('line_note', 'Note'),
    ], string='Display Type', default=False, help=(
        'Technical field for UI purposes only. A Section row is a pure organizational '
        'header (e.g. "Transport", "Documentation", "Out-of-pocket") with no amount, '
        'vendor, or expense of its own -- every real transaction still lives in its own '
        'ordinary line underneath it. A Note row is free text with no amount either.'
    ))

    # === LINE TYPE ===
    line_type = fields.Selection([
        ('expense', 'Cost'),
        ('charge', 'Revenue'),
        ('other', 'Other / Credit'),
    ], string='Line Type', default='expense')

    # === AMOUNTS ===
    budgeted_amount = fields.Float(
        'Budgeted Amount',
        default=0.0,
        digits=(16, 2),
        tracking=True,
        help='Planned amount for this budget line'
    )
    actual_amount = fields.Float(
        'Actual Amount',
        default=0.0,
        digits=(16, 2),
        tracking=True,
        help='Actual cost/revenue incurred'
    )
    variance_amount = fields.Float(
        'Variance',
        compute='_compute_variance',
        store=True,
        digits=(16, 2),
        help='Difference between actual and budgeted amounts'
    )
    amount_company_currency = fields.Float(
        'Amount in Company Currency',
        compute='_compute_amount_company_currency',
        store=True,
        digits=(16, 2)
    )

    # === VENDOR/CUSTOMER ===
    partner_id = fields.Many2one(
        'res.partner',
        string='Vendor/Customer',
        tracking=True,
        help='Supplier or customer for this budget line'
    )

    # === REFERENCES ===
    product_id = fields.Many2one('product.product', string='Product/Service', tracking=True)
    account_id = fields.Many2one(
        'account.account',
        string='Account',
        help='Optional account for future accounting integration'
    )

    # === DETAILS ===
    description = fields.Text('Detailed Description')

    # === DATES ===
    date_planned = fields.Date('Planned Date')
    date_actual = fields.Date('Actual Date')

    # === STATUS ===
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('done', 'Done'),
    ], string='Status', default='draft', tracking=True)

    # === ALREADY-COVERED-BY-A-DOCUMENT INTEGRATION ===
    account_move_id = fields.Many2one(
        'account.move',
        string='Invoice/Bill',
        tracking=True,
        domain=[('state', '=', 'posted')],
        ondelete='set null',
        help='If this line\'s actual amount is already represented by a posted invoice/bill '
             '(e.g. one already linked to the parent record), link it here instead of entering '
             'the amount manually. When set, no expense is auto-created for this line and the '
             'line does not separately contribute to any cost/revenue ledger — the '
             'invoice/bill\'s own posting is what counts.'
    )
    
    source_reference = fields.Reference(
        selection=[('account.move', 'Invoice/Bill')],
        string="Source",
        compute='_compute_source_reference',
        help='The document actually backing this line\'s actual amount. Bridge modules '
             'that add another actualization mechanism (e.g. budgets_hr_expense) extend '
             'this selection and override the compute to add their own fallback.',
    )

    @api.depends('account_move_id')
    def _compute_source_reference(self):
        for line in self:
            line.source_reference = f'account.move,{line.account_move_id.id}' if line.account_move_id else False

    # === HOOKS FOR INDUSTRY-SPECIFIC MODULES TO OVERRIDE ===
    def _get_anchor_record(self):
        """Return the parent business record this line belongs to (e.g. a trade or a
        production order), used for validation and chatter. Empty recordset by default."""
        return self.env['operations.budget.line']

    def _get_anchor_link_vals(self):
        """Return extra vals (e.g. {'trade_id': ...}) identifying this line's anchor,
        to merge into any backing document an actualization backend creates (e.g. an
        hr.expense). Empty dict means "no anchor to attach" -- a backend may treat
        that as a reason to refuse creating the document."""
        return {}

    def _get_display_name_prefix(self):
        """Human-readable prefix (e.g. a trade or file number) used to format the
        auto-generated expense name as "{prefix} / {line name}"."""
        return ''

    def _notify_anchor_of_amount_change(self):
        """Called whenever an amount/line_type/account_move_id changes, so an industry
        module can recompute its own aggregates (e.g. a budget header's totals, or a
        trade's additional_costs/additional_revenue ledger). No-op by default."""
        return

    def _get_conversion_company(self):
        """Company to use for currency conversion / expense company_id. Override to
        point at the anchor's own company if it differs from the current user's."""
        return self.env.company

    def _get_target_currency(self):
        """Currency to convert amount_company_currency into. Defaults to this line's
        own currency (i.e. no conversion) since the core model doesn't know the
        anchor's reporting currency."""
        return self.currency_id

    def _sync_actual_source(self):
        """Hook for an actualization backend to create/update/remove the document
        that backs this line's actual_amount (e.g. an hr.expense). No-op by default:
        a line with no backend simply trusts actual_amount/account_move_id as entered.
        Override in a bridge module (see budgets_hr_expense) to plug in a concrete
        mechanism -- the core model deliberately has no opinion on how actuals are
        realized, only on what a budget line is."""
        return

    # === COMPUTED FIELDS ===
    @api.depends('budgeted_amount', 'actual_amount')
    def _compute_variance(self):
        """Compute variance between budgeted and actual amounts.

        Deliberately side-effect-free (no anchor notification here): writing to other
        records from inside a compute method is fragile in Odoo (recompute/flush
        ordering). create()/write() below call _notify_anchor_of_amount_change()
        explicitly and safely instead, covering every case this would have."""
        for line in self:
            line.variance_amount = line.actual_amount - line.budgeted_amount

    @api.depends('actual_amount', 'budgeted_amount', 'currency_id')
    def _compute_amount_company_currency(self):
        """Convert amounts to the industry's target currency for aggregation."""
        for line in self:
            company = line._get_conversion_company()
            target_currency = line._get_target_currency()
            amount = line.actual_amount or line.budgeted_amount or 0.0

            if line.currency_id and target_currency and line.currency_id != target_currency:
                line.amount_company_currency = line.currency_id._convert(
                    amount, target_currency, company, fields.Date.today()
                )
            else:
                line.amount_company_currency = amount

    # === ONCHANGE ===
    @api.onchange('actual_amount', 'budgeted_amount')
    def _onchange_amounts(self):
        """Force live recomputation on the anchor while editing in the UI."""
        self._notify_anchor_of_amount_change()

    @api.onchange('account_move_id')
    def _onchange_account_move_id(self):
        """Convenience prefill only — the linked move is the actual source of truth,
        this just saves a manual re-entry when nothing has been entered yet."""
        if self.account_move_id and not self.actual_amount:
            self.actual_amount = abs(self.account_move_id.amount_total)
            self.date_actual = self.account_move_id.invoice_date or self.account_move_id.date

    @api.onchange('display_type')
    def _onchange_display_type(self):
        """When a line becomes a Section/Note, clear every field that wouldn't make
        sense on it -- mirrors sale.order.line's _onchange_display_type. When it's
        turned back into a normal line, line_type needs a real default again."""
        if self.display_type:
            self.update({
                'line_type': False,
                'budgeted_amount': 0.0,
                'actual_amount': 0.0,
                'partner_id': False,
                'product_id': False,
                'account_id': False,
                'date_planned': False,
                'date_actual': False,
                'account_move_id': False,
            })
        elif not self.line_type:
            self.line_type = 'expense'

    # === CONSTRAINTS ===
    @api.constrains('budgeted_amount', 'actual_amount')
    def _check_positive_amounts(self):
        """Ensure amounts are positive. Section/note rows are always 0.0 and skipped."""
        for line in self:
            if line.display_type:
                continue
            if line.budgeted_amount < 0:
                raise ValidationError(_("Budgeted amount cannot be negative for line '%s'.") % line.name)
            if line.actual_amount < 0:
                raise ValidationError(_("Actual amount cannot be negative for line '%s'.") % line.name)

    @api.constrains('display_type', 'line_type')
    def _check_line_type_required(self):
        """A real (non-section/note) line must have a line_type; a section/note must not."""
        for line in self:
            if not line.display_type and not line.line_type:
                raise ValidationError(_("Line '%s' must have a Line Type (Cost/Revenue/Other).") % (line.name or ''))
            if line.display_type and line.line_type:
                raise ValidationError(_("A Section/Note line cannot have a Line Type."))

    @api.constrains('display_type', 'account_move_id')
    def _check_no_document_on_section(self):
        """A section/note can never be linked to a real invoice/bill. Bridge modules
        that add another backing-document field (e.g. expense_id) extend this same
        check with their own @api.constrains method."""
        for line in self:
            if line.display_type and line.account_move_id:
                raise ValidationError(_("A Section/Note line cannot be linked to an Invoice/Bill."))

    # === METHODS ===
    def action_confirm(self):
        """Confirm the budget line."""
        for line in self:
            line.write({'state': 'confirmed'})

    def action_done(self):
        """Mark the budget line as done."""
        for line in self:
            line.write({'state': 'done'})

    def _get_initial_tracking_values(self, vals):
        """Get initial field values before write for tracking purposes."""
        initial_values = {}
        tracked_fields = self._fields
        for line in self:
            initial_values[line.id] = {}
            for field_name in vals.keys():
                if field_name in tracked_fields and getattr(tracked_fields[field_name], 'tracking', False):
                    initial_values[line.id][field_name] = line[field_name]
        return initial_values

    def _check_anchor_supports_chatter(self, anchor):
        """Validate the anchor contract implied by _get_anchor_record(): a truthy
        anchor is expected to be a mail.thread-compatible record, since it's used
        for message_post(). A client that overrides _get_anchor_record() to return
        something else gets a clear, actionable error here instead of an opaque
        AttributeError deep inside the ORM the next time a tracked field changes."""
        if not hasattr(anchor, 'message_post'):
            raise ValidationError(_(
                "Budget line anchor '%s' (model '%s') does not support chatter. "
                "_get_anchor_record() must return a record that inherits mail.thread, "
                "or return an empty recordset if this line has no anchor."
            ) % (anchor.display_name, anchor._name))

    def _post_tracking_messages(self, vals, initial_values):
        """Post tracking messages to the anchor record for tracked field changes."""
        if self._context.get('mail_notrack'):
            return

        tracked_fields = self._fields
        for line in self:
            anchor = line._get_anchor_record()
            if not anchor:
                continue
            line._check_anchor_supports_chatter(anchor)

            changes = {}
            for field_name in vals.keys():
                if field_name not in tracked_fields:
                    continue
                field_info = tracked_fields[field_name]
                if not getattr(field_info, 'tracking', False):
                    continue

                old_value = initial_values.get(line.id, {}).get(field_name)
                new_value = line[field_name]
                if old_value != new_value:
                    field_string = field_info.string or field_name
                    old_display = line._format_tracking_value(field_name, old_value, field_info)
                    new_display = line._format_tracking_value(field_name, new_value, field_info)
                    changes[field_string] = (old_display, new_display)

            if changes:
                body_parts = [f"{field}: {old_val} → {new_val}" for field, (old_val, new_val) in changes.items()]
                body = f"Budget line '{line.name}' updated: {', '.join(body_parts)}"
                anchor.message_post(
                    body=body,
                    subtype_xmlid='mail.mt_note',
                    author_id=self.env.user.partner_id.id
                )

    def _format_tracking_value(self, field_name, value, field_info):
        """Format a field value for display in tracking messages."""
        if value is False or value is None:
            return _('(empty)')

        field_type = field_info.type
        if field_type == 'many2one':
            return value.name if value else _('(empty)')
        elif field_type in ('many2many', 'one2many'):
            return ', '.join(value.mapped('name')) if value else _('(empty)')
        elif field_type == 'selection':
            return dict(field_info.selection).get(value, value) if field_info.selection else str(value)
        elif field_type == 'boolean':
            return _('Yes') if value else _('No')
        elif field_type in ('float', 'monetary'):
            if hasattr(field_info, 'get_digits'):
                digits = field_info.get_digits(self.env) or (16, 2)
            else:
                digits = getattr(field_info, '_digits', None) or (16, 2)
            return f"{value:,.{digits[1]}f}"
        else:
            return str(value)

    # === CRUD ===
    @api.model_create_multi
    def create(self, vals_list):
        """Create lines, let the actualization backend (if any) sync for any that
        already carry a positive actual amount, and notify each anchor (some anchors,
        like a trade's additive ledger, have nothing that recomputes automatically on
        record creation). Section/note rows skip all of this — they have nothing to
        sync."""
        lines = super().create(vals_list)
        for line in lines:
            if line.display_type:
                continue
            line._sync_actual_source()
            line._notify_anchor_of_amount_change()
        return lines

    def write(self, vals):
        """Track field changes, sync the actualization backend, and notify the anchor
        of amount/source changes."""
        initial_values = self._get_initial_tracking_values(vals)
        result = super().write(vals)

        self._post_tracking_messages(vals, initial_values)

        if any(f in vals for f in ('actual_amount', 'line_type', 'account_move_id')):
            for line in self:
                if line.display_type:
                    continue
                line._sync_actual_source()

        if any(f in vals for f in ('actual_amount', 'budgeted_amount', 'line_type', 'account_move_id')):
            for line in self:
                if line.display_type:
                    continue
                line._notify_anchor_of_amount_change()

        return result