# Omnifreight Operations - Freight Manufacturing Integration

This module integrates Omnifreight freight operations with Odoo's manufacturing module, allowing you to create work orders from freight quotations and manage the entire freight process through manufacturing workflows.

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
- **No Stock Movement**: Services don't affect inventory but can be used in BOMs

### 2. Manufacturing Order Integration
- **Quotation Link**: Manufacturing orders can be linked to freight quotations
- **Service Selection**: Automatically detects which services (FOB, Freight, LOD) are selected
- **Route Information**: Inherits route, ports, and container information from quotations
- **Cost Tracking**: Displays estimated costs for each service type

### 3. Work Order Management
- **Automatic Generation**: Creates work orders for each selected service
- **Progress Tracking**: Monitor the status of each freight service operation
- **Cost Attribution**: Track costs per service type

## Configuration (Settings → Freight Operations)

Client-specific values are configured per company rather than hardcoded, so
this module can be deployed for a freight client other than Omnifreight
without editing Python. **Every setting falls back to the value that used to
be hardcoded**, so an existing database behaves identically until configured.

| Setting | Falls back to | Why it matters |
|---|---|---|
| Freight Service Product Category | a category named `Omnifreight Services` | the fallback silently no-ops if that category is renamed or absent |
| Bill Validation Approver Group | `base.group_erp_manager` | who may validate vendor bills |
| FOB / Freight / Destination Workcenter | a fuzzy `ilike` name match, then auto-creating one | the fallback can match an unrelated workcenter (e.g. any name containing "fob") and quietly creates master data — configuring these makes service routing deterministic |
| Reconciliation Tolerance Accounts | codes `655000` / `755000` | chart-of-accounts specific; the defaults are Belgian and will misclassify on any other CoA |
| Bank Charge Patterns | a built-in English regex list | language- and bank-specific |
| Internal Transfer Keywords | a built-in English keyword list | language- and bank-specific |

Service scope is also settable directly on the product (**Service Scope** on
the product template). When left empty, the BOM falls back to guessing the
scope from words in the product's name — see the note on
`_infer_service_scope_from_name` for a documented quirk in that guess.

### Still hardcoded

The `fob` / `freight` / `lod` service-type triad is still a Python `Selection`
spread across ~17 files, not configurable data. A client with a different set
of service types cannot be supported without a schema migration; that is
tracked separately from this configuration work.

## How to Use

### Step 1: Create a Freight Quotation
1. Go to **Sales > Quotations** and create a new quotation
2. Select a **Service Scope** (e.g., FOB + Freight + DAP)
3. Configure route, ports, container details, and costs
4. Save the quotation

### Step 2: Create Manufacturing Order
1. In the quotation form, click **"Create Manufacturing Order"**
2. This automatically creates a manufacturing order linked to the quotation
3. The manufacturing order inherits all freight service information

### Step 3: Generate Work Orders
1. In the manufacturing order, go to the **"Freight Operations"** tab
2. Click **"Generate Freight Work Orders"**
3. This creates separate work orders for each selected service:
   - FOB Service Work Order
   - Freight Service Work Order  
   - LOD Service Work Order

### Step 4: Manage Work Orders
1. Go to **Manufacturing > Freight Operations > Work Orders**
2. Each work order represents a specific freight service
3. Use standard manufacturing workflow:
   - **Start** work order when service begins
   - **Finish** work order when service completes
   - Track time and progress

## Menu Structure

### Freight Operations Menu
- **Manufacturing Orders**: View all freight-related manufacturing orders
- **Work Orders**: Manage individual freight service work orders

### Views and Filters
- **Freight Quotations**: Filter manufacturing orders by quotation
- **Service Types**: Filter by FOB, Freight, or LOD services
- **Freight Status**: Track progress (Draft, Confirmed, In Progress, Completed)

## Technical Details

### Models Extended
- `mrp.production`: Manufacturing orders with freight capabilities
- `mrp.workorder`: Work orders with freight service tracking
- `mrp.bom.line`: BOM lines supporting omni_service products
- `sale.order`: Quotations with manufacturing order creation

### Key Fields
- `quotation_id`: Links manufacturing order to quotation
- `freight_state`: Tracks freight operation status
- `freight_service_type`: Identifies service type in work orders
- `service_cost`: Cost tracking per service

### Work Centers
- **FOB Operations**: Handles origin operations
- **Freight Operations**: Manages ocean freight
- **LOD Operations**: Handles destination operations

## Configuration

### Required Setup
1. **Product Category**: "Omnifreight Services" category must exist
2. **Service Products**: FOB, Freight, and LOD service products
3. **Work Centers**: Dedicated work centers for each service type

### Dependencies
- `base`: Core Odoo functionality
- `product`: Product management
- `mrp`: Manufacturing module
- `sale`: Sales and quotation management

## Benefits

1. **Process Integration**: Seamless flow from quotation to execution
2. **Service Tracking**: Monitor each freight service separately
3. **Cost Management**: Track costs per service type
4. **Workflow Management**: Use familiar manufacturing workflows for freight
5. **Reporting**: Generate reports on freight operations
6. **Resource Planning**: Plan and allocate resources for freight services

## Example Workflow

1. **Customer Request**: Customer requests FOB + Freight + DAP service
2. **Quotation**: Sales team creates quotation with route and cost estimates
3. **Manufacturing Order**: Operations team creates manufacturing order from quotation
4. **Work Orders**: System generates three work orders (FOB, Freight, LOD)
5. **Execution**: Each service is executed and tracked through its work order
6. **Completion**: All services complete, manufacturing order finished
7. **Delivery**: Customer receives completed freight service

## Support

For technical support or questions about this module, please contact the development team.

---

**Note**: This module requires the Omnifreight Quotation module to be installed and configured properly.
