import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { optimizeTrajectory, optimizationProblem, optimizationCost, optimizationMetrics, optimizationClearance, type XY } from '../src/algorithms/optimization.ts';
const reference = JSON.parse(readFileSync(new URL('../experiments/original/18/qa/experiment.json', import.meta.url), 'utf8'));
const near = (a: number, b: number, tolerance = 1e-7) => assert(Math.abs(a - b) < tolerance, `${a} != ${b}`);
test('episode18 initial resampling, integral and exact clearance match Python', () => {
  const { initial, discs } = optimizationProblem(), metrics = optimizationMetrics(initial, discs);
  initial.forEach((q, i) => q.forEach((v, j) => near(v, reference.initial_path[i][j], 1e-12)));
  near(metrics.cost, reference.initial_metrics.cost); near(metrics.smooth, reference.initial_metrics.smooth); near(metrics.obstacle, reference.initial_metrics.obstacle); near(metrics.length, reference.initial_metrics.length_m); near(metrics.clearance, reference.initial_metrics.min_clearance_m);
});
test('episode18 analytic gradient differentiates the same quadrature objective', () => {
  const { initial, discs } = optimizationProblem(), p = initial.map((q, i) => q.map((v, j) => v + (i > 0 && i < 40 ? .021 * Math.sin(i * 2.7 + j) : 0)) as XY), direction = p.map((_, i) => i > 0 && i < 40 ? [Math.sin(i * 1.7), Math.cos(i * .8)] as XY : [0, 0] as XY);
  const h = 1e-6, plus = p.map((q, i) => q.map((v, j) => v + h * direction[i][j]) as XY), minus = p.map((q, i) => q.map((v, j) => v - h * direction[i][j]) as XY), gradient = optimizationCost(p, discs, true).gradient;
  const fd = (optimizationCost(plus, discs).cost - optimizationCost(minus, discs).cost) / (2 * h), analytic = gradient.reduce((sum, q, i) => sum + q[0] * direction[i][0] + q[1] * direction[i][1], 0);
  near(fd, analytic, 1e-5);
});
test('episode18 CHOMP 140 rounds reproduces original result and preserves endpoints', () => {
  const frames = [...optimizeTrajectory({ method: 'chomp' })], final = frames.at(-1)!;
  assert.equal(final.iteration, 140); near(final.cost, reference.chomp.final.cost, 2e-7); near(final.length, reference.chomp.final.length_m, 2e-6); near(final.clearance, reference.chomp.final.min_clearance_m, 2e-7); assert(final.collisionFree);
  for (const [i, frame] of frames.entries()) { assert.deepEqual(frame.path[0], frames[0].path[0]); assert.deepEqual(frame.path.at(-1), frames[0].path.at(-1)); if (i) assert(frame.cost <= frames[i - 1].cost + 1e-12); }
});
test('episode18 STOMP is deterministic, accepts only descent and keeps endpoints', () => {
  const run = () => [...optimizeTrajectory({ method: 'stomp', seed: 17, iterations: 30 })], a = run(), b = run();
  assert.deepEqual(a, b); assert(a.at(-1)!.cost < a[0].cost);
  for (const [i, frame] of a.entries()) { assert.deepEqual(frame.path[0], a[0].path[0]); assert.deepEqual(frame.path.at(-1), a[0].path.at(-1)); if (i) assert(frame.cost <= a[i - 1].cost + 1e-12); }
});
test('episode18 pure gradient symmetry failure remains honestly uncertified', () => {
  const frames = [...optimizeTrajectory({ method: 'chomp', scene: 'symmetry', iterations: 80 })];
  assert(!frames.at(-1)!.collisionFree); assert(frames.every(f => f.path.every(q => Math.abs(q[1]) < 1e-14)));
});
test('episode18 collision checking rejects averages of feasible paths and catches edges', () => {
  const ex = reference.averaging_counterexample, discs = [{ center: [2.5, 0] as XY, radius: .65 }];
  assert(optimizationClearance(ex.upper, discs) > 0); assert(optimizationClearance(ex.lower, discs) > 0); assert(optimizationClearance(ex.average, discs) < 0);
  near(optimizationClearance([[0, 0], [5, 0]], discs), -.65);
});
test('episode18 rejects unbounded and non-finite optimization parameters', () => {
  for (const options of [{ iterations: 501 }, { iterations: -1 }, { sigma: NaN }, { sigma: 0 }, { seed: Infinity }]) assert.throws(() => [...optimizeTrajectory({ method: 'stomp', ...options })]);
});
