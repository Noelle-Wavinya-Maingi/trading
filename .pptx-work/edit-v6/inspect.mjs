import { FileBlob, PresentationFile } from '@oai/artifact-tool';
const p = await PresentationFile.importPptx(await FileBlob.load('/Users/noellemaingi/Documents/trading/deck-output/odoo-story-complete-no-repetition-v5.pptx'));
const snap = await p.inspect({kind:'slide,textbox,shape,notes,layout', maxChars:50000});
console.log(snap.ndjson);
