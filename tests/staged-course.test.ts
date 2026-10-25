import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {lessons} from '../src/content/catalog.ts';
const manifest=JSON.parse(readFileSync(new URL('../public/media/manifest.json',import.meta.url),'utf8'));
test('18 lectures match manifest; old full videos remain and new videos are explicitly pending',()=>{
 assert.deepEqual(lessons.map(x=>x.id),Array.from({length:18},(_,i)=>String(i+1).padStart(2,'0')));
 assert.deepEqual(manifest.chapters.map((x:any)=>x.id),lessons.map(x=>x.id));
 for(const lesson of lessons){
  const media=manifest.chapters.find((x:any)=>x.id===lesson.id);
  assert.ok(readFileSync(new URL('../public/'+media.article,import.meta.url),'utf8').startsWith('# '));
  if(Number(lesson.id)<=14){assert.notEqual(lesson.videoStatus,'pending');assert.ok(media.video);assert.match(media.sha256,/^[a-f0-9]{64}$/);}
  else{assert.equal(lesson.videoStatus,'pending');assert.equal(media.videoStatus,'pending');assert.equal(media.video,null);}
 }
});
test('pending videos have a separate UI branch, not broken playback controls',()=>{
 const source=readFileSync(new URL('../src/main.ts',import.meta.url),'utf8');
 const section=source.slice(source.indexOf('const videoSection ='),source.indexOf('content.innerHTML = `${videoSection}'));
 const pendingBranch=section.split('    : `')[0];
 assert.match(pendingBranch,/videoStatus === "pending"/);assert.match(pendingBranch,/视频待补/);
 assert.ok(!pendingBranch.includes('<video'));assert.ok(!pendingBranch.includes('video.mp4'));
 assert.equal(source.split('<div class="topbar-right">').length,2,'host portal adapter remains compatible');
});
