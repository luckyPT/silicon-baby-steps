import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync,readdirSync} from 'node:fs';
import {lessons} from '../src/content/catalog.ts';
import {renderPlatformVideoSection} from '../src/ui/platform-video.ts';
const manifest=JSON.parse(readFileSync(new URL('../public/media/manifest.json',import.meta.url),'utf8'));
test('26 contiguous lectures have structured articles and two official platform videos',()=>{
 assert.deepEqual(lessons.map(x=>x.id),Array.from({length:26},(_,i)=>String(i+1).padStart(2,'0')));
 assert.deepEqual(manifest.chapters.map((x:any)=>x.id),lessons.map(x=>x.id));
 for(const lesson of lessons){const media=manifest.chapters.find((x:any)=>x.id===lesson.id);assert.match(readFileSync(new URL('../public/'+media.article,import.meta.url),'utf8'),/^# /);assert.equal(lesson.videoStatus,'external');assert.equal(media.videoStatus,'external');assert.equal(media.video,null);assert.deepEqual(media.platformVideos.map((v:any)=>v.platform).sort(),['douyin','toutiao']);}
});
test('all course pages including introduction use external video controls and keep portal adapter',()=>{
 const source=readFileSync(new URL('../src/main.ts',import.meta.url),'utf8');
 assert.doesNotMatch(source,/<video|video\.mp4|download MP4/);
 assert.match(source,/const videoSection = renderPlatformVideoSection\(id\)/);
 assert.match(source,/renderPlatformVideoSection\("00"\)/);
 assert.match(renderPlatformVideoSection('26'),/头条观看/);assert.match(renderPlatformVideoSection('26'),/抖音观看/);
 assert.equal(source.split('<div class="topbar-right">').length,2);
});
test('19–26 replay data are finite, contain selectable phases, and preserve real failure states',()=>{
 for(let i=19;i<=26;i++){
  const d=JSON.parse(readFileSync(new URL(`../public/experiments/${i}.json`,import.meta.url),'utf8'));
  assert.equal(d.episode,i);assert.equal(d.mode,'recorded-experiment');assert.ok(d.views.length>=3);
  for(const v of d.views){assert.equal(v.bounds.length,4);for(const point of v.path){assert.equal(point.length,2);assert.ok(point.every(Number.isFinite));}assert.ok(Object.keys(v.metrics).length);}
 }
 for(const i of [23,24,25,26]){const d=JSON.parse(readFileSync(new URL(`../public/experiments/${i}.json`,import.meta.url),'utf8'));assert.ok(d.views.some((v:any)=>v.path.length===0),`${i} must keep its no-path or incomplete query`);}
});
test('public assets contain no video files or chunks',()=>{
 const files=readdirSync(new URL('../public/',import.meta.url),{recursive:true});
 assert.equal(files.filter(p=>/\.(mp4|webm|mov|m4s|m3u8|part\d+)$/i.test(String(p))).length,0);
});
