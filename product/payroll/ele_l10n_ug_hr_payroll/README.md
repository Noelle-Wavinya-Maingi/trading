# Elewa Uganda Payroll

Uganda payroll localization for **Odoo 19 Enterprise**. It adds a monthly salary
structure, payroll inputs, employee fields and salary rules using the shared
[`ele_payroll_ug`](../ele_payroll_ug/README.md) calculation addon.

The technical name is `ele_l10n_ug_hr_payroll`: `ele` identifies Elewa, `l10n`
means localization, and `ug` identifies Uganda.

## What it includes

- **Uganda: Employee** salary structure type and **Uganda: Regular Monthly Pay** structure.
- PAYE, employee and employer NSSF, and automatic Local Service Tax (LST).
- Cash allowances, taxable benefits, reimbursements and other deductions.
- Employee TIN and NSSF number, plus tax treatment and NSSF coverage on the employment version.
- Payslip validation and the standard Odoo payslip report.

## Requirements and installation

Requires `hr_payroll` from Odoo Enterprise and `ele_payroll_ug` from this repository.
Add the Enterprise addons directory and `product/payroll` to your Odoo addons
path, update the Apps list and install **Uganda - Payroll**. The addon is also
configured to install automatically when both dependencies are installed.

## Set up an employee

1. Set the company country to Uganda and use UGX wages.
2. Configure the employee's employment record with a fixed monthly wage and monthly pay schedule.
3. Select **Uganda: Employee** as the salary structure type.
4. Set **Uganda tax treatment** to **Resident**.
5. Set **Uganda NSSF coverage** to **Covered** or **Exempt**. An exemption requires a reason.
6. Record the employee's TIN and NSSF number where available.

The Uganda employee fields are restricted to users with Payroll access.

## Create a payslip

Select **Uganda: Regular Monthly Pay** and a full calendar month starting from
July 2026. Generate work entries, enter any supported inputs, and compute the
payslip. Review the resulting lines before confirming it.

| Input code | Effect in the supplied rules |
| --- | --- |
| `ELE_UG_CASH_ALW` | Adds cash earnings used in the tax and NSSF bases. |
| `ELE_UG_BENEFIT` | Adds taxable value without adding cash earnings. |
| `ELE_UG_REIMBURSE` | Adds a reimbursement to net pay. |
| `ELE_UG_OTHER_DED` | Deducts an amount from net pay. |

Input amounts must be finite and non-negative. The rules apply deduction signs.
Basic salary uses Odoo's `paid_amount`, so mid-month hires and terminations are
prorated through native work entries while the payslip covers the full month.

## Current limits

The current implementation accepts resident, single-employment payroll with
one overlapping employment version and one non-cancelled Uganda payslip per
employee per month. It rejects:

- Periods before July 2026 and payslip periods shorter than a full calendar month.
- Non-resident or multiple-employment tax treatment.
- Employment version changes within the month.
- Refund payslips and active salary attachments.
- Unpaid work entries other than Odoo's `OUT` entries.
- Unrecognized input codes or incomplete NSSF configuration.

## Parameters and maintenance

The supplied parameter values are in `data/hr_rule_parameters_data.xml`; salary
formulas are in `data/hr_salary_rule_data.xml`. The calculation helpers receive
these parameters through the payslip. Review effective dates and values before
using a new payroll period; the code has no upper date cutoff.

Keep calculation logic in `ele_payroll_ug` and Odoo integration in this addon.
Update calculation and payslip tests when changing parameters or formulas.

## Tests

From the repository root, using an environment with Odoo's dependencies:

```bash
python /path/to/odoo/odoo-bin -c /path/to/odoo.conf \
  -d ele_uganda_payroll_test -i ele_l10n_ug_hr_payroll \
  --test-enable --test-tags /ele_l10n_ug_hr_payroll --stop-after-init
```

Use a disposable database. The configuration must include Odoo core, Enterprise
and this repository's `product/payroll` addons paths. Tests cover installation,
payslip calculations, inputs, exemptions, duplicate prevention, proration,
multiple employees and report rendering.

## Upgrading an existing installation

The previous technical name was `l10n_ug_hr_payroll`. The folder rename does not
migrate an installed database. Before upgrading a database using the old name,
back it up and migrate the module identity and external IDs. Do not install the
renamed addon alongside the old one. The included salary-rule migration is not
a module-rename migration.

Maintained by Elewa Company Limited. License: LGPL-3.
