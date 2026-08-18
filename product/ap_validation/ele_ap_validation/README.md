# Vendor Bill Validation Workflow

Adds an approval status to vendor bills, separate from the accounting state:
**draft → awaiting validation → validated**, with rejection capturing a reason
on the chatter.

## Depends on
`account`, `hr_expense`

**No freight, manufacturing or budgeting dependency.** Any client needing bill
approval can install this on its own.

## Why this is a separate module

This workflow used to live in `omni_ops/models/ele_accounting.py`, which mixed
it with freight shipment fields (ports, vessel, container size). Those fields
are `related=` through freight fields on `sale.order`, so the workflow could not
be installed without the entire freight stack — including `quotation` and `mrp`.

Extracting it was a **file split, not a file move**: the shipment fields stayed
behind in `omni_ops` as its own `account.move` extension, and only the workflow
came here.

## What this module adds

- **`status`** on `account.move` — an approval state independent of `state`.
- **Two routing paths**:
  - *Management* — schedules an activity for a member of the configured approver
    group.
  - *Operations* — raises an `hr.expense` from the bill; approving that expense
    validates the bill.
- **Two wizards** (`wizard/`): validation (choose route, add a note, confirm) and
  rejection (capture a reason).
- **`bill_reference`** on `hr.expense`, linking an expense back to its bill, plus
  an `action_post` override: company-account expenses do **not** get Odoo's
  auto-generated payment move, because the linked vendor bill is the real
  accounting record.

## Configuration (Settings → Bill Validation)

| Setting | Falls back to |
|---|---|
| Bill Validation Approver Group | `base.group_erp_manager` |

The fallback preserves the previous hardcoded behaviour, so an existing database
is unaffected until configured.

## Design notes

- Wizards live in `wizard/` with their views, per Odoo convention — they are
  `TransientModel`s, not persisted records.
- `_get_management_user` picks the highest-id member of the approver group. That
  "last user wins" heuristic is inherited behaviour and is questionable; it is
  preserved deliberately rather than changed as a side effect of the extraction.

## Automated tests

None yet. The approval workflow, the expense-raising path and the
`action_post` override are all untested — worth covering before this module is
relied on by a second client.
