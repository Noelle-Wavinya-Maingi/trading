# Operations

`operations` lets a company declare which industry it operates in — Shipping,
Trading, or Manufacturing — and automatically provisions the right modules,
pipeline stages, and defaults for that choice. It's the layer that ties the
rest of this suite together: `quotation`, `trading`, and manufacturing
support all sit downstream of the industry selected here.

## What this module provides

**Industry selection.** A `res.config.settings` extension exposes
`company_industry` (Shipping/Trading/Manufacturing) alongside an
`industry.type` reference model holding each industry's defaults — income
and expense accounts, default journal.

**Automatic module provisioning.** Choosing an industry and saving installs
the corresponding module — `quotation` for Shipping, `trading` for Trading,
`mrp` for Manufacturing — through a dedicated install helper
(`_install_operations_modules`).

**Industry-scoped workflow stages.** `workflow.stage` records are created
per industry on setup (e.g. Draft → Confirmed → Processing → Shipped → Done
for Trading), giving each industry its own kanban/pipeline stages out of the
box.

**Industry lock/unlock.** Once an industry is selected and saved, it locks,
preventing accidental changes; a system administrator can explicitly unlock
it to switch industries later.

## Notes

`_install_operations_modules` is named deliberately to avoid colliding with
`res.config.settings`'s own internal module-installation method of a similar
name — a naming collision there would silently override core Odoo's handling
of *every* module toggle on the settings form, not just this module's own.