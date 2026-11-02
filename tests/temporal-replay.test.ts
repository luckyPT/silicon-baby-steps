import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {sampleAt} from '../src/ui/temporal-lab.ts';
const data=JSON.parse(readFileSync(new URL('../public/experiments/27.json',import.meta.url),'utf8'));
test('recorded crossing preserves its wait and the baseline collision at t=4',()=>{
 const s=data.views[0].timeSeries;
 assert.deepEqual(sampleAt(s.path,3.5),[4,3]);
 assert.deepEqual(sampleAt(s.baseline,4),[5,3]);
 assert.deepEqual(sampleAt(s.obstacles[0],4),[5,3]);
 assert.deepEqual(sampleAt(s.path,5),[5,3]);
 assert.deepEqual(sampleAt(s.path,16),[9,3]);
});
test('recorded swap keeps its failed result and exposes collision between safe endpoints',()=>{
 const s=data.views[3].timeSeries;
 assert.deepEqual(s.path,[]);
 assert.notDeepEqual(sampleAt(s.baseline,0),sampleAt(s.obstacles[0],0));
 assert.notDeepEqual(sampleAt(s.baseline,1),sampleAt(s.obstacles[0],1));
 assert.deepEqual(sampleAt(s.baseline,.5),sampleAt(s.obstacles[0],.5));
 assert.equal(data.views[4].metrics.arrival_s,null);
 assert.equal(data.views[1].metrics.arrival_s,11);
});
