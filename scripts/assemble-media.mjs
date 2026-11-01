// Reconstruct exact original MP4 bytes from versioned <=10MiB chunks.
import {readFile,writeFile,mkdir,rename,stat,unlink} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {resolve,dirname} from 'node:path';
const root=resolve(import.meta.dirname,'..');
const manifest=JSON.parse(await readFile(resolve(root,'course-media/manifest.json'),'utf8'));
for(const v of manifest.videos){
 const out=resolve(root,v.output);let existing;
 try{existing=await readFile(out);}catch{}
 if(existing&&existing.length===v.bytes&&createHash('sha256').update(existing).digest('hex')===v.sha256)continue;
 const parts=[];
 for(const p of v.parts){const data=await readFile(resolve(root,p.path));if(data.length!==p.bytes||createHash('sha256').update(data).digest('hex')!==p.sha256)throw Error('Invalid video part: '+p.path);parts.push(data);}
 const data=Buffer.concat(parts);if(data.length!==v.bytes||createHash('sha256').update(data).digest('hex')!==v.sha256)throw Error('Invalid assembled video: '+v.id);
 await mkdir(dirname(out),{recursive:true});await writeFile(out+'.assembling',data);await rename(out+'.assembling',out);console.log('Restored full video '+v.id);
}
