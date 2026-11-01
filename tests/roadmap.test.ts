import test from 'node:test';
import assert from 'node:assert/strict';
import { buildRoadmap, compareRoadmaps, roadmapEdgeValid, roadmapPointValid, shortestRoadmapPath } from '../src/algorithms/roadmap.ts';

test('roadmap segment check rejects collisions despite valid endpoints and handles degenerate segments', () => {
  assert(roadmapPointValid([1, -.65])); assert(roadmapPointValid([2.2, -.65]));
  assert(!roadmapEdgeValid([1, -.65], [2.2, -.65]));
  assert(roadmapEdgeValid([0, 0], [0, 0]));
  assert(!roadmapEdgeValid([1.6, -.65], [1.6, -.65]));
  assert(!roadmapEdgeValid([0, -2], [6, -2]));
  assert(!roadmapEdgeValid([1, -.2], [2.2, -.2])); // Tangency is collision.
});
test('roadmap is deterministic and candidate edges are unique, bounded and undirected', () => {
  const a = buildRoadmap(17, 90, 6); assert.deepEqual(a, buildRoadmap(17, 90, 6));
  assert.equal(a.vertices.length, 90); assert(a.vertices.every(roadmapPointValid));
  assert.equal(new Set(a.edges.map(e => e.join(','))).size, a.edges.length);
  assert(a.edges.every(([i, j]) => i >= 0 && i < j && j < 90));
  assert.throws(() => buildRoadmap(1, 20, 20)); assert.throws(() => buildRoadmap(1, 501, 2));
});
for (const seed of [1, 7, 17]) test(`PRM/Lazy same graph has same safe shortest path cost, seed ${seed}`, () => {
  const report = compareRoadmaps({ seed });
  assert.equal(report.eagerTotalChecks, report.eagerBaseChecks + 60);
  for (const q of report.queries) {
    assert(q.lazyPath.length > 1); assert(q.allReturnedSegmentsCollisionFree);
    assert(Math.abs(q.eagerCost! - q.lazyCost!) < 1e-8);
    assert(q.lazyPath.slice(1).every((b, i) => roadmapEdgeValid(q.vertices[q.lazyPath[i]], q.vertices[b])));
    assert(q.initialKnownEdges.every(x => x.edge.every(v => v < report.n)), 'query attachments must never leak into shared cache');
    assert.equal(q.lazyChecks, q.trace.reduce((s, t) => s + t.tested.length, 0));
    assert.equal(q.trace.at(-1)!.invalid, null);
    assert(q.trace.slice(0, -1).every(t => t.invalid !== null));
  }
});
test('graph search reports disconnected graph instead of passing unknown reachability as success', () => {
  assert.deepEqual(shortestRoadmapPath([[0, 0], [1, 0]], [], new Map(), 0, 1), { path: [], cost: null });
  assert.deepEqual(shortestRoadmapPath([[0, 0], [1, 0]], [[0, 1]], new Map([['0,1', false]]), 0, 1), { path: [], cost: null });
  const report = compareRoadmaps({ seed: 1, n: 20, k: 1 });
  for (const q of report.queries) assert.equal(q.eagerCost, q.lazyCost);
});
