import fs from 'node:fs/promises';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { Presentation, PresentationFile } from '@oai/artifact-tool';

const workspaceDir='/Users/noellemaingi/Documents/trading';
const TMP_DIR=path.join(workspaceDir,'.deck-build');
const SKILL_DIR='/Users/noellemaingi/.codex/plugins/cache/openai-primary-runtime/presentations/26.904.11930/skills/presentations';
const FINAL_PPTX=path.join(workspaceDir,'deck-output','commodity-module-masterpiece.pptx');
const RUNTIME_PYTHON='/Users/noellemaingi/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3';
const {finalizePresentation}=await import(pathToFileURL(path.join(SKILL_DIR,'container_tools/artifact_tool_utils.mjs')).href);
const p=Presentation.create({slideSize:{width:1280,height:720}});
const C={blue:'#1723BC',lime:'#D8FF3E',cream:'#FFF8E8',ink:'#171729',pink:'#FF6E9E',orange:'#FF9255',white:'#FFFFFF'};
const font='Arial';
function txt(s,t,x,y,w,h,size,color,bold=false){let q=s.shapes.add({geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});q.text=t;q.text.style={typeface:font,fontSize:size,bold,color,autoFit:'none'};return q}
function slide(bg){let s=p.slides.add();s.background.fill=bg;return s}
function note(s,t){s.speakerNotes.textFrame.setText(t)}

// 1. Cover
{
 let s=slide(C.blue);const img=await fs.readFile(path.join(TMP_DIR,'cover.png'));
 s.images.add({blob:new Uint8Array(img),contentType:'image/png',alt:'Editorial illustration of cocoa beans and copper tokens',fit:'cover',position:{left:0,top:0,width:1280,height:720}});
 txt(s,'COMMODITY\nTRADING',72,145,700,235,88,C.white,true);
 txt(s,'The module I built to make every trade make sense',78,485,670,90,29,C.lime,true);
 note(s,'The cover artwork is an AI generated editorial illustration. Product facts throughout come from product/commodity_trading/ele_trading/README.md.');
}
// 2. The problem
{
 let s=slide(C.cream);txt(s,'THE PROBLEM',72,62,500,55,28,C.blue,true);
 txt(s,'A trade is one story.\nOdoo sees separate documents.',72,145,1120,170,56,C.ink,true);
 txt(s,'A purchase can sell in pieces, on different dates and in different currencies. Without a shared trade record, position and profit have to be reconciled outside the normal workflow.',72,395,1080,175,31,C.ink);
 note(s,'Source: product/commodity_trading/ele_trading/README.md, sections 1 and 2.');
}
// 3. What it is
{
 let s=slide(C.lime);txt(s,'WHAT IT IS',72,62,500,55,28,C.blue,true);
 txt(s,'ONE TRADE',72,155,1080,120,105,C.blue,true);
 txt(s,'A central record that connects purchases, sales, invoices and stock activity in Odoo.',78,318,1060,160,38,C.ink,true);
 txt(s,'The team keeps using familiar order screens. The module builds the trading ledger as those documents are confirmed.',78,545,1080,105,25,C.ink);
 note(s,'Source: product/commodity_trading/ele_trading/README.md, sections 1, 3 and 4.');
}
// 4. What happens
{
 let s=slide(C.blue);txt(s,'HOW IT WORKS',72,60,600,55,28,C.lime,true);
 txt(s,'BUY',70,170,310,100,76,C.white,true);txt(s,'A confirmed purchase opens or updates a trade.',70,280,325,180,27,C.white);
 txt(s,'SELL',475,170,310,100,76,C.lime,true);txt(s,'Confirmed sales attach to the trade, even when the position sells in parts.',475,280,325,200,27,C.white);
 txt(s,'SEE',875,170,310,100,76,C.pink,true);txt(s,'Open quantity and P&L update. Fully matched trades close automatically.',875,280,325,200,27,C.white);
 txt(s,'One position, kept current from the work people already do.',72,592,1100,80,31,C.lime,true);
 note(s,'Source: product/commodity_trading/ele_trading/README.md, sections 1, 4 and 6.');
}
// 5. Capabilities
{
 let s=slide(C.cream);txt(s,'WHAT IT DOES',72,62,600,55,28,C.blue,true);
 txt(s,'POSITION',72,150,510,72,52,C.blue,true);txt(s,'Tracks bought, sold and still open quantity.',72,230,495,96,27,C.ink);
 txt(s,'PROFIT',675,150,510,72,52,C.blue,true);txt(s,'Shows realized P&L and market based unrealized P&L.',675,230,505,125,27,C.ink);
 txt(s,'TRUE COST',72,410,510,72,52,C.blue,true);txt(s,'Includes linked bills and invoices in the trade picture.',72,490,500,105,27,C.ink);
 txt(s,'REAL WORLD',675,410,510,72,52,C.blue,true);txt(s,'Handles transaction date FX and tracks physical stock separately.',675,490,510,125,27,C.ink);
 note(s,'Source: product/commodity_trading/ele_trading/README.md, sections 2, 4, 6, 7 and 9. Market price is entered by a user.');
}
// 6. Why this product
{
 let s=slide(C.pink);txt(s,'WHY THIS PRODUCT',72,60,700,55,28,C.blue,true);
 txt(s,'Because the deal\nshould stay visible.',72,155,1120,200,70,C.ink,true);
 txt(s,'It puts the commercial position, actual costs and profit in the same place as the orders that created them.',78,400,1100,150,34,C.ink);
 txt(s,'That is the masterpiece: turning scattered transactions into a trade you can follow.',78,596,1110,65,29,C.blue,true);
 note(s,'This slide states the product rationale based on product/commodity_trading/ele_trading/README.md, sections 1 and 2. “Masterpiece” reflects the presenter’s own description.');
}

await fs.mkdir(path.dirname(FINAL_PPTX),{recursive:true});
for(let i=0;i<p.slides.length;i++){const data=await p.export({slide:p.slides.getByIndex(i),format:'png',scale:1});await fs.writeFile(path.join(TMP_DIR,`slide-${i+1}.png`),new Uint8Array(await data.arrayBuffer()));}
const stagingDir=path.join(workspaceDir,'.codex-finalizer');await fs.mkdir(stagingDir,{recursive:true});
const candidatePath=path.join(stagingDir,'candidate.pptx');await (await PresentationFile.exportPptx(p)).save(candidatePath);
const result=await finalizePresentation({workspaceDir,candidatePath,finalPath:FINAL_PPTX,pythonExecutable:RUNTIME_PYTHON,integrityValidatorPath:path.join(SKILL_DIR,'container_tools/inspect_presentation_package_integrity.py'),layoutValidatorPath:path.join(SKILL_DIR,'container_tools/inspect_presentation_layout_geometry.py'),layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-bullet-geometry','--validate-heading-fit'],fontPolicy:{basis:'design',families:[font]},verifyArtifactToolImport:true,receiptPath:path.join(stagingDir,'commodity-module.validation.json')});
console.log(JSON.stringify(result));
