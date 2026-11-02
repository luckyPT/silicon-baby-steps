import { readFile, access, readdir } from 'node:fs/promises';
import { resolve } from 'node:path';
import { lessons } from '../src/content/catalog.ts';
import { platformVideos, videosForLesson, validatePlatformVideo, pendingForLesson } from '../src/content/platform-videos.ts';
const root=resolve(import.meta.dirname,'../public');
const manifest=JSON.parse(await readFile(resolve(root,'media/manifest.json'),'utf8'));
const ids=manifest.chapters.map(m=>m.id);
if(new Set(ids).size!==lessons.length || JSON.stringify(ids)!==JSON.stringify(lessons.map(l=>l.id)))throw Error('Catalog and external-media manifest must contain the same lessons');
for(const id of Object.keys(platformVideos))if(id!=='00'&&!ids.includes(id))throw Error(`Unknown video lesson: ${id}`);
for(const m of manifest.chapters){
 const lesson=lessons.find(l=>l.id===m.id);
 if(m.video!==null||m.videoStatus!=='external'||lesson.videoStatus!=='external')throw Error(`Local media must be disabled: ${m.id}`);
 const pending=pendingForLesson(m.id);
 if(JSON.stringify(m.platformVideos)!==JSON.stringify(videosForLesson(m.id))||JSON.stringify(m.pendingPlatforms??[])!==JSON.stringify(pending))throw Error(`Platform states disagree: ${m.id}`);
 const targets=[...m.platformVideos.map(v=>v.platform),...pending].sort();
 if(JSON.stringify(targets)!==JSON.stringify(['douyin','toutiao']))throw Error(`Both platforms need a verified link or explicit pending state: ${m.id}`);
 m.platformVideos.forEach(validatePlatformVideo);
 await access(resolve(root,m.cover));
 const article=await readFile(resolve(root,m.article),'utf8');
 if(!article.startsWith('# ')||!article.includes('## '))throw Error(`Missing structured article: ${m.id}`);
 for(const match of article.matchAll(/!\[[^\]]*\]\(([^)]+)\)/g)){if(!match[1].startsWith('../media/'))throw Error(`Article image URL is not supported by the runtime media resolver: ${m.id}`);await access(resolve(root,'articles',match[1]));}
 if(Number(m.id)>=19){const d=JSON.parse(await readFile(resolve(root,`experiments/${m.id}.json`),'utf8'));if(d.episode!==Number(m.id)||d.mode!=='recorded-experiment'||!d.views.length)throw Error(`Missing real replay: ${m.id}`);}
 console.log(`${m.id}: article, cover, figures and exact published/pending platform states verified`);
}
if(manifest.introduction.video!==null||!videosForLesson('00').length)throw Error('Introduction must use a platform link');
await access(resolve(root,manifest.introduction.poster));
async function noPayload(dir){for(const e of await readdir(dir,{withFileTypes:true})){const p=resolve(dir,e.name);if(e.isDirectory())await noPayload(p);else if(/\.(mp4|webm|mov|mkv|m4s|m3u8|part\d+)$/i.test(e.name))throw Error(`Video payload must not be shipped: ${p}`);}}
await noPayload(root);
console.log(`${lessons.length} lecture chapters + introduction verified; no local video payloads.`);
