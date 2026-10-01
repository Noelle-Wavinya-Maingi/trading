# Uganda payroll calculations

Reusable calculation helpers for Elewa's Uganda payroll addons on Odoo 19.
This addon depends on `hr` and works with Community or Enterprise. Payslip
structures and employee configuration live in
[`ele_l10n_ug_hr_payroll`](../ele_l10n_ug_hr_payroll/README.md).

## What it provides

| Function | Purpose |
| --- | --- |
| `resident_paye()` | Applies progressive income bands and a surcharge above a supplied threshold. |
| `nssf_contribution()` | Multiplies the supplied cash wage base by a contribution rate. |
| `lst_installment()` | Finds a consistent PAYE/LST result and returns the installment for a configured collection month. |

The helpers return `Decimal` values. Callers supply bands, rates and collection
settings; the helpers do not load company settings or round to a currency.
Invalid amounts raise `ValueError`. LST also raises an error when its bands do
not produce exactly one consistent result.

## Installation

Add `product/payroll` to the Odoo addons path and install `ele_payroll_ug`.
Installing the Enterprise localization also installs this dependency.
There are no menus or user settings in this addon.

## Use from another addon

Declare `ele_payroll_ug` in your manifest's `depends` list, then import the
required helper:

```python
from decimal import Decimal
from odoo.addons.ele_payroll_ug.models.ele_calculations import nssf_contribution

# Illustrative inputs; the caller supplies the applicable rate.
contribution = nssf_contribution(Decimal('1000000'), Decimal('0.05'))
```

Keep rates in the calling addon's configuration. Round the result when applying
it to a payslip currency.

## Tests

From the repository root, using your configured Odoo Python environment:

```bash
python /path/to/odoo/odoo-bin -c /path/to/odoo.conf \
  -d ele_payroll_helpers_test -i ele_payroll_ug \
  --test-enable --test-tags /ele_payroll_ug --stop-after-init
```

Use a disposable database and include `product/payroll` in the configuration's
addons path. The tests cover PAYE boundaries, contribution calculations and LST
collection behavior.

## Maintenance

Calculation functions are in `models/ele_calculations.py`; their tests are in
`tests/test_ele_calculations.py`. Add boundary tests when changing a formula.

Maintained by Elewa Company Limited. License: LGPL-3.
