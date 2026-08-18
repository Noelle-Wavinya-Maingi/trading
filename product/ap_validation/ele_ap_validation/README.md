# Vendor Bill Validation Workflow

Adds an approval status to vendor bills, separate from the accounting state:
**draft → awaiting validation → validated**, with rejection capturing a reason
on the chatter.

## Depends on
`account`, `hr_expense`

That is the whole dependency list — no freight, manufacturing or budgeting
dependency, so any client needing bill approval can install this on its own.

## What this module adds

- **`ele_status`** on `account.move` — an approval state independent of `state`.
- **Two routing paths**:
  - *Management* — schedules an activity for a member of the configured approver
    group.
  - *Operations* — raises an `hr.expense` from the bill; approving that expense
    validates the bill.
- **Two wizards** (`wizard/`): validation (choose route, add a note, confirm) and
  rejection (capture a reason).
- **`ele_bill_reference`** on `hr.expense`, linking an expense back to its bill,
  plus an `action_post` override: company-account expenses do **not** get Odoo's
  auto-generated payment move, because the linked vendor bill is the real
  accounting record.

## Configuration (Settings → General Settings → Accounting → Vendor Bills)

| Setting | Falls back to |
|---|---|
| Bill Validation Approver Group | `base.group_erp_manager` |

The fallback means an unconfigured database still works, defaulting to the
same access group that already manages Settings.

## Design notes

- Wizards live in `wizard/` with their views, per Odoo convention — they are
  `TransientModel`s, not persisted records.
- `_get_management_user` picks the highest-id member of the approver group. That
  "last user wins" heuristic is inherited, longstanding behaviour; it is
  preserved deliberately rather than changed as a side effect of packaging.

## Packaging

- `static/description/icon.png` and `static/description/index.html` — store
  listing page
- `i18n/ele_ap_validation.pot` — translation template
- `demo/demo.xml` — points the approver group at a non-default group so an
  evaluator can see the setting is actually wired up
- `'application': True` in the manifest, so it shows as an installable app

## Automated tests

None yet. The approval workflow, the expense-raising path and the
`action_post` override are all untested — worth covering before this module is
relied on by a second client.
