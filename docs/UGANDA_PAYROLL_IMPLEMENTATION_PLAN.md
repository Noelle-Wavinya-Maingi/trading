# Uganda payroll localization — implementation plan

Status: initial common-module and Enterprise-adapter skeletons implemented.
The Enterprise adapter installs and its five installation tests pass locally.
Salary calculations and coexistence verification remain unfinished.
Target: Odoo 19 Enterprise `hr_payroll`; Community integration is a later phase.

## Gap

This repository has an initial Uganda payroll skeleton, but no operational
statutory salary rules. Matching Enterprise 19 source was located at
`/Users/noellemaingi/Downloads/enterprise-19.0` and used with the local Odoo
19 core for installation verification.

## Why it matters

A localization built against the wrong payroll version can fail to install
or calculate incorrectly. Uganda also changed resident monthly PAYE bands
on 1 July 2026: a UGX 500,000 chargeable income yields UGX 38,250 under the
new bands, compared with UGX 52,000 in URA's old-rate example. Applying one
undated formula to all periods would miscalculate historical payroll.

## Smallest correct fix

Create `product/payroll/ele_payroll_ug/`, depending on Enterprise
`hr_payroll`. Use an initial manifest version of `19.0.1.0.0` and country
metadata for Uganda. Do not create a separate payroll engine or generic
base addon yet; extract a common extension only when Uganda and Tanzania
demonstrate a concrete need that native payroll does not meet.

After the matching Enterprise source is available:

1. Inspect the native Kenyan localization and native payroll tests as
   implementation references. Reuse APIs and conventions without copying
   licensed Enterprise source into this repository.
2. Add Uganda structure type, regular monthly salary structure, rule
   categories, input types and salary rules under the addon's `data/`.
3. Use native dated rule parameters for statutory rates and thresholds,
   with independently verified start dates. Explicitly reject periods
   outside the supported range rather than silently applying current rates.
4. Add only necessary Uganda employee/payroll-version fields and views:
   residency treatment, tax identifiers and NSSF eligibility/registration.
   Inspect the Odoo 19 contract/version model before choosing where
   period-sensitive settings live. Unset tax treatment must not silently
   default to resident. Exemption settings need an explicit explanation.
5. Implement PAYE, employee NSSF and employer NSSF as separate rules.
   Employer contributions must not reduce employee net pay. Establish gross
   cash pay, chargeable income and contribution wages separately; do not
   assume all three bases are identical.
6. Include local service tax requirements in the statutory specification
   before calling the module a complete monthly payroll localization.
   Verify assessment bands, exemptions, collection schedule and PAYE
   treatment from the relevant authority. Do not guess these rules.
7. Reuse native payslip reporting initially, adding Uganda information only
   where necessary. Statutory filing exports require the current official
   templates and validation rules; an ordinary CSV is not an approved return.
8. Keep optional accounting integration in
   `product/payroll/ele_payroll_ug_account/`, depending on the localization
   and `hr_payroll_account`. Configure accounts per company rather than
   assuming an identical chart of accounts for every employer.

## Statutory evidence collected on 18 September 2026

| Subject | Verified evidence | Implementation consequence |
|---|---|---|
| Resident PAYE | URA's 7 September 2026 notice explicitly states new bands apply from 1 July 2026 | Date the new parameters; test the effective-date transition |
| Non-resident PAYE | URA publishes a distinct non-resident table | Separate treatment; confirm effective dates against the legislation before seeding historical values |
| Multiple employment | URA describes a flat 30% treatment | Specify eligibility and interaction with other tax treatments before implementing |
| Standard NSSF | NSSF states employee 5% and employer 10% of gross monthly wages | Keep the two contributions separate and validate eligibility and the wage base |
| Local service tax | URA guidance describes a deduction before PAYE | Verify current local-government assessment and collection rules before implementing |

Sources:

- [URA: Income Tax (Amendment) Act 2026 PAYE notice](https://ura.go.ug/en/changes-to-paye-return-form-following-the-income-tax-amendment-act-2026/)
- [URA: current PAYE tables and multiple employment](https://ura.go.ug/en/domestic-taxes/paye-rates/)
- [NSSF: membership and standard contributions](https://www.nssfug.org/about-us/membership/)
- [URA: general FAQs, including local service tax](https://ura.go.ug/en/general-faqs/)

The current PAYE page and older URA FAQs contain different historical
thresholds. Use dated legislation/notices to resolve applicability; never
treat a page's crawl date as a rate's legal effective date. Taxable benefits,
exemptions, arrears, termination pay, rounding and filing formats still need
an explicit sourced specification.

## Boundary risks

- Placement follows `docs/ONBOARDING_A_NEW_VERTICAL.md`: country payroll is
  a product domain, so it belongs under `product/payroll/`, not `shared/`.
  The container is an addons-path root, not a Python package.
- New fields on native models use `ele_ug_` names. Native conventional
  fields retain their native names. New methods use country-specific names;
  overrides preserve `super()` behavior.
- Preserve native payroll access groups and existing record rules. Any new
  independent business model needs its own ACLs and company isolation.
  Sensitive identifiers must not become available through public employee
  views or unrestricted fields.
- Do not introduce trade, freight or budget dependencies. Both countries
  must eventually coexist, with no edits to one country's rules caused by
  installing the other.
- Update root README addons paths, `tools/pre_commit_check.sh`,
  `tools/verify_boundaries.sh` and `.github/workflows/verify-boundaries.yml`
  alongside the addon. Add a payroll change filter and Enterprise-only
  install/tests and coexistence scenarios. Community runs must clearly
  skip the Enterprise addon; missing Enterprise credentials must not count
  as evidence of successful payroll verification.
- Subsequent schema changes require version bumps and migrations following
  `docs/MIGRATIONS.md`.

## Verification plan

Before considering implementation complete:

1. Parse XML and run the repository collision scanner and applicable lint
   checks. A pre-commit run with nothing staged does not verify an addon.
2. Install and run the localization tests against Odoo 19 Enterprise in a
   uniquely named throwaway database with demo data. Record the actual
   test summary and prove the module is installed.
3. Test end-to-end payslip calculation against independently established
   expected values, including URA's UGX 500,000 example. Cover exact bands,
   just below/above bands, the additional high-income rate, resident and
   non-resident treatment, eligibility, and employee/employer contribution
   separation.
4. Test June/July 2026 historical applicability once both dated schedules
   are established, unsupported periods, and month-crossing periods.
   Establish a policy for multiple payslips in a month, arrears and refunds;
   do not accidentally grant a fresh monthly threshold to every slip.
5. Reproduce calculation scenarios through the live ORM. For regression
   fixes, retain evidence that the new test fails against the pre-fix
   behavior as required by `docs/TESTING.md`.
6. Prove company isolation with two companies and restricted payroll users
   in a real database, including access to the newly added sensitive fields.
7. Run Enterprise coexistence with the existing trading and freight
   verticals, preserving the standalone budget test databases. Confirm
   installing Uganda payroll does not change another country's rules.
8. Verify repeat installation/upgrade preserves configuration and historical
   payslip behavior. Validate filing exports against official templates
   before claiming filing support.

Local verification on 18 September 2026: both modules installed with demo
data in a throwaway Odoo 19 Enterprise database. After correcting an error
message mismatch, the adapter tests reported `0 failed, 0 error(s) of 5 tests`.
This establishes configuration and the missing-rules safeguard, not correct
PAYE/NSSF calculations, multi-company isolation, coexistence, or GitHub CI.
