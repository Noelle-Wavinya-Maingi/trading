import fs from 'node:fs/promises';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {Presentation,PresentationFile} from '@oai/artifact-tool';

const root='/Users/noellemaingi/Documents/trading';
const skill='/Users/noellemaingi/.codex/plugins/cache/openai-primary-runtime/presentations/26.904.11930/skills/presentations';
const py='/Users/noellemaingi/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3';
const out=path.join(root,'deck-output','commodity-module-overview-v3.pptx');
const {finalizePresentation}=await import(pathToFileURL(path.join(skill,'container_tools/artifact_tool_utils.mjs')).href);
const p=Presentation.create({slideSize:{width:1280,height:720}});
const C={paper:'#F7F5EF',ink:'#142333',muted:'#4A5967',blue:'#1D425F',rust:'#B95A38',line:'#C9C6BC',white:'#FFFFFF'};
const F={head:'Georgia',body:'Arial'};
function box(s,t,x,y,w,h,size,color=C.ink,bold=false,f=F.body){const a=s.shapes.add({geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});a.text=t;a.text.style={typeface:f,fontSize:size,bold,color,autoFit:'none'};return a}
function slide(n,kicker,title,sub=''){const s=p.slides.add();s.background.fill=C.paper;box(s,kicker.toUpperCase(),70,42,950,35,17,C.rust,true);box(s,title,70,91,1140,92,48,C.ink,false,F.head);if(sub)box(s,sub,72,190,1100,66,22,C.muted);box(s,String(n).padStart(2,'0'),1170,660,45,30,17,C.muted);return s}
function notes(s,t){s.speakerNotes.textFrame.setText(t)}
function item(s,head,body,x,y,w){box(s,head,x,y,w,40,26,C.blue,true);box(s,body,x,y+48,w,125,23,C.ink)}

// 1 cover
{
 const s=p.slides.add();s.background.fill=C.ink;
 box(s,'ELEWA  /  PRODUCT OVERVIEW',74,58,900,30,19,'#DAB29D',true);
 box(s,'Commodity\ntrading',72,160,1040,210,86,C.white,false,F.head);
 box(s,'A single view of the position, the economics and the documents behind every trade.',78,465,1030,115,31,C.white);
 box(s,'Built in Odoo',78,627,950,35,19,'#DAB29D');
 notes(s,'Source for all product claims: product/commodity_trading/ele_trading/README.md and product/commodity_trading/ele_trading_budget/README.md. ');
}
// 2 agenda
{
 const s=slide(2,'The route','Agenda');
 item(s,'01  The problem','Why standard purchase and sale records lose the thread of a trade.',80,215,495);
 item(s,'02  The product','The central trade record and its workflow inside Odoo.',670,215,495);
 item(s,'03  The detail','Position, P&L, FX, extra costs and physical stock.',80,450,495);
 item(s,'04  The value','Why one connected trade view matters to the business.',670,450,495);
 notes(s,'Agenda reflects the structure of this presentation.');
}
// 3 problem
{
 const s=slide(3,'The problem','Trading spans more than one document','A commodity position evolves after the first purchase or sale.');
 item(s,'Partial sales','One purchase may be sold in several orders, at different prices and dates.',75,300,345);
 item(s,'Mixed currencies','The purchase and subsequent sales may use different currencies.',465,300,345);
 item(s,'True profitability','Freight, storage and other bills can change the actual result.',855,300,345);
 box(s,'Without a shared trade record, the team has to reconcile the position and profit outside Odoo.',76,574,1110,65,27,C.rust,true);
 notes(s,'Source: ele_trading README, sections 1 and 2.');
}
// 4 overview
{
 const s=slide(4,'The product','The Trade is the central record','The module derives it from the Odoo documents the team already uses.');
 item(s,'Purchase orders','A confirmed purchase opens or updates a long trade.',75,292,345);
 item(s,'Sale orders','A confirmed sale links to an open trade. If none exists, it can open a short trade.',465,292,345);
 item(s,'Bills and stock','Linked invoices affect extra cost or revenue. Validated receipts link stock lots.',855,292,345);
 box(s,'The result: one connected ledger for the commercial position and its financial outcome.',76,587,1110,62,27,C.rust,true);
 notes(s,'Source: ele_trading README, sections 1, 3 and 4. “Ledger” is descriptive language, not a separate general ledger feature.');
}
// 5 lifecycle
{
 const s=slide(5,'Workflow','A trade follows the deal','The record changes as orders are confirmed and the position is sold down.');
 item(s,'1  Open','Confirm a purchase order. The trade captures product, quantity, price and currency.',74,287,345);
 item(s,'2  Sell down','Confirm one or more sales. Sold quantity and the open position update.',465,287,345);
 item(s,'3  Close','When purchase and sale quantities fully match, the confirmed trade closes automatically.',856,287,345);
 box(s,'Short trades can start from a sale when no matching open trade exists.',76,584,1100,65,25,C.muted);
 notes(s,'Source: ele_trading README, section 4 and auto-close logic in section 6.');
}
// 6 metrics
{
 const s=slide(6,'Economics','The position and P&L stay visible','An illustrative long trade shows how the main measures relate.');
 box(s,'100 units',75,275,300,55,43,C.blue,true);box(s,'purchased',77,332,300,36,22,C.muted);
 box(s,'40 units',475,275,300,55,43,C.blue,true);box(s,'sold',477,332,300,36,22,C.muted);
 box(s,'60 units',875,275,300,55,43,C.rust,true);box(s,'still open',877,332,300,36,22,C.muted);
 item(s,'Realized P&L','Sales value less the average cost of the matched 40 units.',76,447,500);
 item(s,'Unrealized P&L','Market price compared with the cost of the 60 open units.',672,447,500);
 notes(s,'Illustrative quantities only, not actual trading data. Source for formulas: ele_trading README, sections 5 and 6. Market price is entered manually. Without a market price, the long trade uses a conservative placeholder for unrealized P&L as documented.');
}
// 7 financial detail
{
 const s=slide(7,'Financial detail','Profit reflects the actual trade','The module keeps extra charges and currency conversion tied to their source dates.');
 item(s,'Transaction date FX','Each purchase or sale converts at its own transaction date into the reporting currency.',76,290,520);
 item(s,'Additional cost and revenue','Linked bills and invoices contribute amounts beyond the original order values.',680,290,520);
 box(s,'A market price can be entered on an open trade to estimate unrealized P&L.',76,548,1100,60,26,C.rust,true);
 notes(s,'Source: ele_trading README, sections 2, 4, 6 and 7. Mixed currency sale prices are converted to the reporting currency before blending.');
}
// 8 inventory
{
 const s=slide(8,'Operational detail','Commercial and physical are different','The module tracks both, because they answer different questions.');
 item(s,'Open position','Purchase quantity less sold quantity. This is the outstanding commercial exposure.',76,292,510);
 item(s,'On hand','Physical inventory from stock lots linked to validated goods receipts.',680,292,510);
 box(s,'These figures can differ while a receipt or delivery is still in progress.',76,555,1090,65,27,C.rust,true);
 notes(s,'Source: ele_trading README, sections 5 and 9.');
}
// 9 extensions
{
 const s=slide(9,'Further capability','Contracts and budgets extend the view','The core trade remains the anchor for additional control.');
 item(s,'Futures contracts','Nested contracts track agreed price and quantity, delivered balance, and contract P&L.',76,290,520);
 item(s,'Optional Trade Budgets','A separate module compares planned cost and revenue with actuals from posted bills, invoices and expenses.',680,290,520);
 box(s,'Budget variance appears once a trade is fully matched.',76,554,1090,65,27,C.rust,true);
 notes(s,'Sources: ele_trading README, section 8, and ele_trading_budget README. Trade Budgets are an optional separate addon.');
}
// 10 rationale
{
 const s=slide(10,'Why this product','A trade deserves one clear picture','The product connects operational work with the outcome the business cares about.');
 item(s,'Less reconciliation','Purchases and sales feed the trade directly as staff confirm them.',75,290,345);
 item(s,'Earlier visibility','Open quantity and realized or unrealized P&L stay available as the deal evolves.',465,290,345);
 item(s,'Better context','Costs, currencies and stock sit beside the commercial position.',855,290,345);
 box(s,'My masterpiece was making the whole trade legible in the system people already use.',76,574,1110,70,28,C.rust,true);
 notes(s,'Product rationale based on ele_trading README, sections 1 and 2. “My masterpiece” reflects the presenter’s own description.');
}

const stage=path.join(root,'.codex-finalizer');await fs.mkdir(stage,{recursive:true});await fs.mkdir(path.dirname(out),{recursive:true});
const candidate=path.join(stage,'candidate-v2.pptx');await (await PresentationFile.exportPptx(p)).save(candidate);
const result=await finalizePresentation({workspaceDir:root,candidatePath:candidate,finalPath:out,pythonExecutable:py,integrityValidatorPath:path.join(skill,'container_tools/inspect_presentation_package_integrity.py'),layoutValidatorPath:path.join(skill,'container_tools/inspect_presentation_layout_geometry.py'),layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-bullet-geometry','--validate-heading-fit'],fontPolicy:{basis:'design',families:[F.head,F.body]},verifyArtifactToolImport:true,receiptPath:path.join(stage,'commodity-module-v3.validation.json')});
console.log(JSON.stringify({finalPath:result.finalPath,layout:result.presentationLayout?.finding_count,slides:result.packageIntegrity?.slide_count}));
