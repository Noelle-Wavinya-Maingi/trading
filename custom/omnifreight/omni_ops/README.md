# Omnifreight Operations - Freight File Process Engine

This module manages Omnifreight freight operations through freight files (`omni.ops.file`) and their operational steps (`omni.ops.step`), generated automatically from configurable step templates when a quotation is confirmed. It no longer depends on or extends Odoo's manufacturing module — the legacy `mrp.production`/work order/BOM path was retired in Phase 5 of `docs/PROCESS_ENGINE_MIGRATION_PLAN.md`.

## Related modules

This module used to also contain budgeting, vendor bill approval and bank
reconciliation. Those were separate concerns bolted into one addon, so they now
live on their own:

| Module | What it does | Depends on freight? |
|---|---|---|
| `omni_budget` | planned-vs-actual budget per freight file | yes — optional add-on to this module |
| `ele_ap_validation` | vendor bill approval workflow | **no** — installable standalone |
| `ele_bank_reconcile` | bank statement match classification | **no** — installable standalone |

`omni_ops` itself no longer depends on `budgets` or `budgets_hr_expense`:
install `omni_budget` to get the budgeting feature, or leave it out.

## Features

### 1. Freight Service Products
- **Omnifreight Service Product Type**: New product type specifically for freight services
- **Service Categories**: FOB, Freight, and LOD (Local at Destination) services
- **No Stock Movement**: Services don't affect inventory

### 2. Freight Files (`omni.ops.file`)
- **Auto-created on confirm**: Confirming a quotation creates a freight file for each qualifying freight service line, linked back to that `sale.order.line`
- **Quotation-derived details**: Route, ports, incoterms, package details, and customer/partner data are computed from the linked sale order
- **Service flags**: `has_fob_service`, `has_freight_service`, `has_lod_service` are computed from the steps generated on the file, and drive which notebook tabs are shown

### 3. Operational Steps (`omni.ops.step`)
- **Generated from templates**: When a freight file is created, the matching `omni.service.step.template` (by service scope) generates its steps onto the file
- **Lifecycle**: each step moves `draft` → `in_progress` → `done` via **Start** and **Done** buttons on the freight file form
- **Sequencing**: steps are ordered by `sequence` and can optionally declare `blocked_by_step_ids`, a dependency on other steps within the same file

## How to Use

### Step 1: Create a Freight Quotation
1. Go to **Sales > Quotations** and create a new quotation
2. Select a **Service Scope** (e.g., FOB + Freight + DAP)
3. Configure route, ports, container details, and costs
4. Save the quotation

### Step 2: Confirm the Quotation
1. Click **Confirm** on the quotation
2. This automatically creates a freight file (`omni.ops.file`) for each qualifying freight service line
3. The step template matching the quotation's service scope generates the file's operational steps

There is no manual "create manufacturing order" or "generate work orders" action — file and step creation both happen as a side effect of confirming the order. If no step template exists for the quotation's service scope, no freight file is created and a warning is posted to the quotation's chatter instructing the user to configure one under **Freight Operations > Configuration > Freight Step Templates**.

### Step 3: Work the Steps
1. Open the freight file (from the quotation's **Sale Order** smart button, or from **Freight Operations > Freight Files**)
2. Each service scope (FOB / Freight / Destination) has its own notebook tab, shown only if the file has steps of that type
3. Use **Start** and **Done** on each step to progress it through `draft` → `in_progress` → `done`

## Menu Structure

### Freight Operations (app menu)
- **Freight Files**: `omni.ops.file` records, created automatically on quotation confirmation
- **Configuration > Freight Step Templates**: `omni.service.step.template` records, one per service scope, defining which steps get generated

## Technical Details

### Key Models
- `omni.ops.file`: the freight file itself; inherits `workflow.mixin` and `mail.thread`; linked to `sale.order.line` via `sale_line_id`
- `omni.ops.step`: an operational step on a freight file; inherits `workflow.step.mixin`; has `service_type` (`fob`/`freight`/`lod`), `sequence`, and `blocked_by_step_ids`
- `omni.service.step.template` / `omni.service.step.template.line`: define, per `service_scope`, which steps to generate onto a new freight file
- `sale.order`: extended with `dispatch.mixin` to create freight files on confirm (`_freight_bridge_definition`) and expose `omni_ops_file_ids`/`omni_ops_file_count`

### Key Fields
- `omni.ops.file.sale_line_id` / `sale_order_id`: link back to the originating quotation
- `omni.ops.file.has_fob_service` / `has_freight_service` / `has_lod_service`: computed from the file's generated steps
- `omni.ops.step.service_type`: identifies which service scope a step belongs to
- `omni.ops.step.state`: `draft` / `in_progress` / `done`
- `omni.service.step.template.service_scope`: the key used to look up the right template when a quotation is confirmed

## Configuration

### Required Setup
1. **Product Category**: "Omnifreight Services" category must exist
2. **Service Products**: FOB, Freight, and LOD service products
3. **Freight Step Templates**: at least one `omni.service.step.template` per service scope the business quotes (e.g. `fob`, `freight`, `lod`, `fob_freight`, `fob_freight_lod`) — without a matching template, confirming a quotation of that scope will not create a freight file

Service scope is also settable directly on the product (**Service Scope** on the product template). `omni_ops` does not add its own Settings (`res.config.settings`) panel. Bill approval and bank reconciliation settings that used to live here now belong to `ele_ap_validation` and `ele_bank_reconcile` respectively — see those modules' own READMEs for their configuration options.

### Still hardcoded

The `fob` / `freight` / `lod` service-type triad is still a Python `Selection`
spread across several files, not configurable data. A client with a different set
of service types cannot be supported without a schema migration; that is
tracked separately from this configuration work.

### Dependencies
- `base`: Core Odoo functionality
- `sale`: Sales and quotation management
- `product`: Product management
- `quotation`: Omnifreight quotation model (route, ports, incoterms, package details)
- `account`: Accounting
- `hr_expense`: Expense tracking
- `stock`: Inventory/UoM support
- `workflow` (`shared/workflow`): provides the generic `workflow.mixin`, `workflow.step.mixin`, and `workflow.template.mixin` that `omni.ops.file`, `omni.ops.step`, and `omni.service.step.template` build on, plus `dispatch.mixin` used by `sale.order` to create freight files on confirm

## Benefits

1. **Process Integration**: Seamless flow from quotation confirmation to freight file and step creation
2. **Service Tracking**: Monitor each freight service scope separately, with its own steps
3. **Workflow Management**: Simple draft/in-progress/done lifecycle per step, with optional step dependencies
4. **Reporting**: Generate reports on freight files and their steps
5. **Configurability**: Which steps get generated is driven by data (step templates), not code

## Example Workflow

1. **Customer Request**: Customer requests FOB + Freight + DAP service
2. **Quotation**: Sales team creates quotation with route and cost estimates
3. **Confirmation**: Confirming the quotation creates the freight file and generates its steps from the matching step template
4. **Execution**: Operations team works through each step, marking it Started then Done
5. **Completion**: All steps for the file reach `done`
6. **Delivery**: Customer receives completed freight service

## Support

For technical support or questions about this module, please contact the development team.

---

**Note**: This module requires the Omnifreight Quotation module (`quotation`) to be installed and configured properly.
