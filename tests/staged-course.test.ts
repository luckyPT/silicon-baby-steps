import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync,readdirSync} from 'node:fs';
import {lessons} from '../src/content/catalog.ts';
import {renderPlatformVideoSection} from '../src/ui/platform-video.ts';
const manifest=JSON.parse(readFileSync(new URL('../public/media/manifest.json',import.meta.url),'utf8'));
test('28 contiguous lectures have structured articles and honest platform states',()=>{
 assert.deepEqual(lessons.map(x=>x.id),Array.from({length:28},(_,i)=>String(i+1).padStart(2,'0')));
 assert.deepEqual(manifest.chapters.map((x:any)=>x.id),lessons.map(x=>x.id));
 for(const lesson of lessons){const media=manifest.chapters.find((x:any)=>x.id===lesson.id);assert.match(readFileSync(new URL('../public/'+media.article,import.meta.url),'utf8'),/^# /);assert.equal(lesson.videoStatus,'external');assert.equal(media.videoStatus,'external');assert.equal(media.video,null);assert.deepEqual([...media.platformVideos.map((v:any)=>v.platform),...(media.pendingPlatforms??[])].sort(),['douyin','toutiao']);}
});
test('all course pages including introduction use external video controls and keep portal adapter',()=>{
 const source=readFileSync(new URL('../src/main.ts',import.meta.url),'utf8');
 assert.doesNotMatch(source,/<video|video\.mp4|download MP4/);
 assert.match(source,/const videoSection = renderPlatformVideoSection\(id\)/);
 assert.match(source,/renderPlatformVideoSection\("00"\)/);
 assert.match(renderPlatformVideoSection('26'),/头条观看/);assert.match(renderPlatformVideoSection('26'),/抖音观看/);
 assert.equal(source.split('<div class="topbar-right">').length,2);
});
test('19–27 replay data are finite, contain selectable phases, and preserve real failure states',()=>{
 for(let i=19;i<=27;i++){
  const d=JSON.parse(readFileSync(new URL(`../public/experiments/${i}.json`,import.meta.url),'utf8'));
  assert.equal(d.episode,i);assert.equal(d.mode,'recorded-experiment');assert.ok(d.views.length>=3);
  for(const v of d.views){assert.equal(v.bounds.length,4);for(const point of v.path){assert.equal(point.length,2);assert.ok(point.every(Number.isFinite));}assert.ok(Object.keys(v.metrics).length);}
 }
 for(const i of [23,24,25,26,27]){const d=JSON.parse(readFileSync(new URL(`../public/experiments/${i}.json`,import.meta.url),'utf8'));assert.ok(d.views.some((v:any)=>v.path.length===0),`${i} must keep its no-path or incomplete query`);}
});
test('public assets contain no video files or chunks',()=>{
 const files=readdirSync(new URL('../public/',import.meta.url),{recursive:true});
 assert.equal(files.filter(p=>/\.(mp4|webm|mov|m4s|m3u8|part\d+)$/i.test(String(p))).length,0);
});

test('episode 28 preserves the computed horizon, track margins and stopped results', () => {
 const data=JSON.parse(readFileSync(new URL('../public/experiments/28.json',import.meta.url),'utf8'));
 assert.equal(data.episode,28);
 assert.equal(data.dt,.1);
 assert.equal(data.views.length,4);
 for(const run of data.views){
  assert.equal(run.states.length,Math.round(run.metrics.duration/data.dt)+1);
  assert.ok(run.states.every((state:number[])=>state.length===5 && state.every(Number.isFinite)));
  if(run.id.startsWith('mpc') || run.id==='disturbance'){
   assert.equal(run.predictions.length,run.states.length-1);
   assert.ok(run.predictions.every((points:number[][])=>points.length===20 && points.every(p=>p.length===2 && p.every(Number.isFinite))));
   assert.ok(run.metrics.minMargin>0);
   assert.ok(run.metrics.endSpeed<.08);
  }else{
   assert.equal(run.predictions.length,0);
   assert.ok(run.metrics.minMargin<0);
  }
 }
 assert.equal(data.views[3].perturbationTime,2.6);
});
