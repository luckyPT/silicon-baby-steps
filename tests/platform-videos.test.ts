import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {platformVideos, videosForLesson, validatePlatformVideo, platformLabels} from '../src/content/platform-videos.ts';
import {renderPlatformVideoSection} from '../src/ui/platform-video.ts';
import {lessons} from '../src/content/catalog.ts';
test('verified public work pages belong to known lessons and exact official hosts',()=>{
  for(const [id,videos] of Object.entries(platformVideos)) {
    assert.ok(id==='00'||lessons.find(l=>l.id===id)); assert.ok(videos.length);
    if(id==='00')continue;
    const article=readFileSync(new URL(`../public/articles/${id}.md`,import.meta.url),'utf8');
    assert.doesNotMatch(article,/完整视频的网页同步待补|网站完整视频另行补齐/,`published episode ${id} must not retain obsolete video-pending copy`);
    for(const video of videos)assert.doesNotThrow(()=>validatePlatformVideo(video));
  }
});
test('platform labels match destinations; verified pages get safe links, not unverified players',()=>{
  for(const [id,videos] of Object.entries(platformVideos)) {
    const html=renderPlatformVideoSection(id);
    for(const video of videos)assert.ok(html.includes(platformLabels[video.platform]+'观看'));
    assert.match(html,/target="_blank" rel="noopener noreferrer"/);
    assert.ok(!html.includes('<iframe'));assert.ok(!html.includes('<video'));assert.ok(!html.includes('<script'));
    assert.ok(!html.includes('视频待补'));assert.match(html,/平台可能要求登录/);
  }
});
test('unknown IDs stay pending, and known episodes use platform links',()=>{
  assert.deepEqual(videosForLesson('99'),[]);
  assert.match(renderPlatformVideoSection('99'),/尚无已核实的公开作品链接/);
  for(const lesson of lessons)assert.equal(lesson.videoStatus,'external');
});
test('reject foreign hosts, private pages, HTTP, credentials and media-CDN links',()=>{
  for(const url of ['http://www.toutiao.com/video/1/','https://www.toutiao.com.evil.test/video/1/','https://user:pass@www.toutiao.com/video/1/','https://mp.toutiao.com/profile_v4/xigua/content-manage','https://www.toutiao.com/video/file.mp4']) {
    assert.throws(()=>validatePlatformVideo({platform:'toutiao',url,verifiedAt:'2026-10-25'}));
  }
});
test('episode 18 keeps its actual work IDs after the migration',()=>{
  const videos=videosForLesson('18');assert.equal(videos.length,2);
  assert.ok(videos.some(v=>v.url.includes('7700843119977218579')));
  assert.ok(videos.some(v=>v.url.includes('7700843660887346483')));
  const html=renderPlatformVideoSection('18');assert.match(html,/头条观看/);assert.match(html,/抖音观看/);assert.doesNotMatch(html,/<video|<iframe|video.mp4/);
});
