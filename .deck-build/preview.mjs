import fs from 'node:fs/promises';
import {FileBlob,PresentationFile} from '@oai/artifact-tool';
const p=await PresentationFile.importPptx(await FileBlob.load('/Users/noellemaingi/Documents/trading/deck-output/odoo-story-complete-no-repetition-v2.pptx'));
for(let i=0;i<15;i++){const d=await p.export({slide:p.slides.getItem(i),format:'png',scale:1});await fs.writeFile(`/Users/noellemaingi/Documents/trading/.deck-build/complete-v2-slide-${i+1}.png`,new Uint8Array(await d.arrayBuffer()));}
