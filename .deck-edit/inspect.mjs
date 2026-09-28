import { FileBlob, PresentationFile } from '@oai/artifact-tool';
const p=await PresentationFile.importPptx(await FileBlob.load('/Users/noellemaingi/Documents/trading/deck-output/odoo-story-complete-no-repetition-v4.pptx'));
const s=await p.inspect({kind:'textbox',maxChars:50000});
console.log(s.ndjson);
