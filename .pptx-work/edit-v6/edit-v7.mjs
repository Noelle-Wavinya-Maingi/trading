import fs from 'node:fs/promises';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { FileBlob, PresentationFile } from '@oai/artifact-tool';

const workspaceDir = '/Users/noellemaingi/Documents/trading';
const sourcePath = path.join(workspaceDir, 'deck-output/odoo-story-complete-no-repetition-v5.pptx');
const finalPath = path.join(workspaceDir, 'deck-output/odoo-story-speaker-script-v7.pptx');
const skillDir = '/Users/noellemaingi/.codex/plugins/cache/openai-primary-runtime/presentations/26.904.11930/skills/presentations';
const pythonExecutable = '/Users/noellemaingi/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3';
const p = await PresentationFile.importPptx(await FileBlob.load(sourcePath));

function replace(id, text) {
  const obj = p.resolve(id);
  obj.text.replace(obj.text.toString(), text);
}
replace('sh/q5wjelsz', 'Accounting, stock, budgets, reporting and the roadmap.');
replace('sh/bq9orito', 'Begin with three prepared trades, then follow the partial trade in detail.');
replace('sh/ove9o7yd', '4  Live walkthrough');
replace('sh/9wnqhczy', 'The full trade journey, from purchase to the final result.');
replace('sh/xcz2l03q', 'Realized plus unrealized P&L, plus additional revenue less additional costs.');
replace('sh/p4r6p8by', '1  Compare');
replace('sh/21gnuts7', 'Start on the trade board and compare open, partial and closed positions.');
replace('sh/32ponyts', '2  Trace');
replace('sh/gzy5s3a1', 'Open the partial trade and trace its orders, currency, lot and quantities.');
replace('sh/1076lobm', '3  Explain');
replace('sh/hcfy9k3u', 'Show P&L, posted additional costs and revenue, budget and reports.');

const notes = [
`OPENING | about 1 minute
“Today I am showing you the commodity trading module, which was my masterpiece. The title is ‘When the Standard Way Isn’t Enough’ because Odoo already handles purchases, sales, stock and accounting very well. The challenge appeared when the business wanted to see those separate events as one commodity trade. I built a central Trade record that connects them and keeps the commercial position and profit visible as the transaction changes.”

Set the expectation that this is a product story and a live walkthrough, not a tour of every Odoo menu.

Source: module documentation and implementation in this repository.`,
`AGENDA | about 45 seconds
“I will begin with commodity trading in plain language, because the room does not need trading knowledge. Then I will explain the gap in the standard flow and the product decision behind the Trade record. After that, I will cover the lifecycle, calculations, currency, inventory, optional budgets and the technical integration. I will finish in Odoo with a complete trade journey from purchase activity to the final result.”

Transition: “First, what does a commodity trader actually need to manage?”`,
`COMMODITY TRADING | about 1 minute
“Commodity trading means buying and selling physical goods such as coffee, cocoa, grain or fuel while prices and currencies can change. A company may buy one batch and sell it in parts, to different customers, on different days. That creates a position: the quantity purchased but not yet sold, or the quantity sold but not yet covered by a purchase. The business needs one answer for the completed part and another for the part that remains exposed.”

Use the example on screen: “If we buy 100 units and sell 40, 40 units have a realized result and 60 units remain open.”

Transition: “Odoo records every document, so why was another module necessary?”`,
`WHY THE PRODUCT WAS NECESSARY | about 1 minute 30 seconds
“Standard Odoo gives us reliable operational documents. Purchase records the buy, Sales records the sell, Inventory records physical movement, and Accounting records bills and invoices. Analytic accounts can group accounting amounts that users allocate to them. Those tools answer their own questions well.”

“The missing piece was a live trade position assembled from all those documents. We needed to know how much of a specific deal was bought, sold, still open, physically on hand and profitable without manually combining several reports. An analytic account can group attributed money, but it does not calculate a commodity position from order quantities or match the bought and sold legs of a trade.”

Transition: “The product decision was to introduce one connecting record.”

Sources: product/commodity_trading/ele_trading/README.md, sections 1 and 2. Odoo analytic accounting documentation: https://www.odoo.com/documentation/19.0/applications/finance/accounting/reporting/analytic_accounting.html`,
`THE TRADE RECORD | about 1 minute 30 seconds
“The Trade is the centre of the module, but users still work through familiar Odoo documents. When a purchase order is confirmed, the module creates or updates a long Trade. When a sale is confirmed, it links to an eligible Trade or opens a short position. Validated receipts attach stock lots. Posted bills and invoices contribute additional cost or revenue when they relate to the trade.”

“The important design principle is that the Trade follows the source documents. A user should not have to copy the same quantity or value into a separate spreadsheet or custom form. The record becomes the place to inspect the whole deal.”

Transition: “Once the Trade exists, its direction and status follow clear rules.”

Source: product/commodity_trading/ele_trading/README.md, sections 1, 3 and 4.`,
`TRADE LIFECYCLE | about 1 minute
“A long trade starts with a purchase. Its open quantity is what we bought less what we have sold. A short trade starts with a sale when there is no matching open purchase trade, so the quantity remains negative until purchases cover it.”

“The state is driven by matching. An open trade still has exposure. A partial trade has some matched quantity and some remaining exposure. A completed long trade closes when the confirmed sold quantity matches the confirmed purchased quantity. This prevents a trade from being called closed simply because someone changed a label.”

Transition: “The state tells us where we are; the calculations tell us what it means financially.”

Source: product/commodity_trading/ele_trading/README.md, sections 4 to 6.`,
`CORE CALCULATIONS | about 1 minute 30 seconds
“There are four measures, and each answers a separate question. Open position is the quantity still exposed. Realized P&L is the result on the matched quantity that has both a purchase and a sale. Unrealized P&L estimates the result on the open quantity using the current market price. Total P&L combines the realized and unrealized results, adds additional revenue and subtracts additional costs.”

“Keeping these measures separate matters. A profitable completed sale does not tell us whether the unsold balance has gained or lost value. The total brings both parts together while preserving the explanation.”

Transition: “A simple example makes the distinction concrete.”

Source: product/commodity_trading/ele_trading/README.md, sections 5 and 6. Market price is entered by a user.`,
`WORKED EXAMPLE | about 1 minute 30 seconds
“We buy 100 units at 10, so the original purchase cost is 1,000. We sell 40 units at 14, giving sales value of 560. The matched 40 units make a realized profit of 160 because the margin is 4 per unit.”

“We still hold an open position of 60. If the current market price is 12, those units carry an unrealized profit of 120. The trade therefore shows total P&L of 280 before any additional costs or revenue. This is the view we could not get by looking at the purchase or sale alone.”

Transition: “Real trades also involve different currencies and later financial documents.”

Illustrative arithmetic. Formula basis: ele_trading README, section 6.`,
`CURRENCY AND FINANCIAL EVENTS | about 1 minute 15 seconds
“The module converts each transaction using the exchange rate for that transaction date. That allows one Trade to contain a purchase in euros, a sale in dollars and reporting in Kenya shillings. When several sales occur at different rates, their reporting values blend correctly.”

“Additional amounts come from actual posted documents beyond the original buy and sell. Freight, inspection or repackaging can arrive through a vendor bill or expense. A quality premium can arrive through a customer invoice. If a linked invoice returns to draft or is removed, the contribution reverses so the Trade stays tied to document lifecycle.”

Transition: “Money and physical stock also describe different aspects of the trade.”

Source: product/commodity_trading/ele_trading/README.md, sections 4, 6 and 7.`,
`COMMERCIAL POSITION AND STOCK | about 1 minute
“Open position comes from confirmed purchase and sale quantities. On hand comes from stock lots connected through validated receipts and deliveries. These quantities can differ legitimately.”

“For example, we may have confirmed a purchase before the goods arrive, so the commercial position exists while on hand is zero. At the other end, a fully delivered closed trade can have a linked lot and zero on hand because all stock has left. The lot preserves traceability; zero on hand describes the current physical balance.”

Transition: “Around this core, the module adds optional planning and reporting.”

Source: product/commodity_trading/ele_trading/README.md, section 9.`,
`OPTIONAL CAPABILITIES AND ROADMAP | about 1 minute 15 seconds
“The optional budget focuses on additional cost and additional revenue, not the original purchase and sale values. Posted freight, inspection, repackaging or a customer premium can feed the budget from bills, invoices and expenses. Once the trade is fully matched, the budget can show the variance and final view.”

“Reporting uses Odoo list, Kanban, graph and pivot views so teams can filter by trade status and profitability. Analytic account integration is planned; the field is hidden in this demo until the transaction level relationship is implemented correctly. Futures and contract level delivery balances also remain roadmap items, so I will not present them as current functionality.”

Transition: “For the technical audience, here is where the behaviour enters Odoo.”

Sources: ele_trading README, sections 8 and 10; ele_trading_budget README.`,
`TECHNICAL DESIGN | about 1 minute 30 seconds
“The core model is trading.trade. The module extends standard Odoo models with a Trade link and hooks into their normal lifecycle. Purchase confirmation creates or updates the purchase side. Sale confirmation finds or creates the sales side. Accounting posting, reset and deletion manage financial contributions. Stock validation connects lots and updates physical quantity.”

“The position and P&L fields are stored computed fields. That choice makes them available to Odoo views, filters and reports while keeping the calculation logic centralized. The value of this design is traceability: when a number changes, we can follow it back to an order, stock movement, bill or invoice.”

Transition: “Now I will show those relationships in the prepared data.”

Implementation references: models/purchase_order.py, sale_order.py, account_move_lifecycle.py, stock_picking.py and trading_trade_pnl.py.`,
`LIVE ODOO WALKTHROUGH | about 7 minutes

0:00–1:00 — Trade board
“Here are three prepared scenarios. Coffee is open because it is purchased and unsold. Cashew is partial because part of the quantity has been sold. Shea is closed because purchase and sale quantities match. The statuses therefore describe position, not manual completion.”

1:00–3:15 — Open the partial Cashew trade
“On this record, the purchase quantity is 100 and the sold quantity is 60, so 40 remains open. I can move from the Trade to the linked purchase and sale documents. The transaction currencies can differ, while the summary reports in the company currency. The lot connects the commercial trade to the physical stock. On hand is 40 here because that balance remains in inventory.”

3:15–4:45 — Explain the financial summary
“The sold cost basis belongs to the 60 matched units. Realized P&L belongs to that sold portion. The market price values the remaining 40 and produces unrealized P&L. Total P&L combines both and then includes additional revenue less additional costs.”

4:45–6:00 — Open Additional Costs and Revenue
“This is separate from the core purchase and sale. The additional cost comes from a posted vendor bill, such as freight or inspection. The additional revenue comes from a posted customer invoice, such as a quality premium. These are actual accounting documents, so we can trace the value and its status. The optional budget collects those extra amounts and gives us a final variance view.”

6:00–7:00 — Compare the closed Shea trade and reporting
“On the closed trade, bought and sold quantities match and the open position is zero. On hand is also zero because the goods have been delivered. The lot remains linked for traceability. The Trade still shows the sold cost basis and nonzero final profit. I will finish on the reporting view to show that these stored measures can be filtered and analysed across trades.”

If time is short, skip the Coffee detail and show Cashew plus Shea.`,
`CLOSING | about 45 seconds
“The standard Odoo flow still performs the transactions. This module gives those transactions a trade context. From one record, the team can see what was bought, what was sold, what remains exposed, what is physically on hand, which extra financial documents belong to the deal and what the current result is.”

“That is the meaning of the title. The standard way was enough to process each event, but the commodity business needed the whole story of the trade.”

Close with: “That was my masterpiece: one Trade record that makes the complete commodity position visible and traceable.”`
];
if (p.slides.items.length !== notes.length) throw new Error(`Expected ${notes.length} slides, got ${p.slides.items.length}`);
for (let i=0; i<notes.length; i++) p.slides.items[i].speakerNotes.textFrame.setText(notes[i]);

const stagingDir = path.join(workspaceDir, '.pptx-work/edit-v6/finalizer');
await fs.mkdir(stagingDir, {recursive:true});
await fs.mkdir(path.dirname(finalPath), {recursive:true});
const candidatePath = path.join(stagingDir, 'candidate.pptx');
await (await PresentationFile.exportPptx(p)).save(candidatePath);
const { finalizePresentation } = await import(pathToFileURL(path.join(skillDir, 'container_tools/artifact_tool_utils.mjs')).href);
const result = await finalizePresentation({
  explicitTotalSlideCount: 14,
  requiredNativeTableOwnerSlides: [],
  requiredNativeChartOwnerSlides: [],
  workspaceDir,
  candidatePath,
  finalPath,
  pythonExecutable,
  integrityValidatorPath: path.join(skillDir, 'container_tools/inspect_presentation_package_integrity.py'),
  layoutValidatorPath: path.join(skillDir, 'container_tools/inspect_presentation_layout_geometry.py'),
  layoutArgs: ['--expected-slide-size-emu','12192000,6858000','--validate-bullet-geometry','--validate-heading-fit'],
  verifyArtifactToolImport: true,
  receiptPath: path.join(stagingDir, 'validation-v7.json')
});
console.log(JSON.stringify({finalPath, result}, null, 2));
