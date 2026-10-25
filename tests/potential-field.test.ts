import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { runPotentialField, pfEdge, pfForces, pfPotential, pfDistance, PF_MODEL, type PFPoint } from '../src/algorithms/potential-field.ts';
const near = (a: number, b: number, eps = 1e-10) => assert(Math.abs(a - b) <= eps, `${a} != ${b}`);
const reference = JSON.parse(readFileSync(new URL('../experiments/original/16/qa/experiment.json', import.meta.url), 'utf8'));
for (const mode of ['baseline', 'subgoal'] as const) test(`episode16 ${mode}: every default waypoint agrees with preserved Python`, () => {
  const result = runPotentialField(mode), ref = reference.runs.find((r: { mode: string }) => r.mode === mode);
  assert.equal(result.status, ref.status); assert.equal(result.iterations, ref.iterations);
  assert.equal(result.planningChecks + result.validationChecks, ref.motion_checks_including_validation);
  near(result.lengthM, ref.length_m); near(result.goalDistanceM, ref.goal_distance_m);
  near(result.minVertexClearanceM, ref.min_vertex_clearance_m);
  assert.equal(result.path.length, ref.path.length);
  result.path.forEach((p, i) => near(pfDistance(p, ref.path[i]), 0));
  assert(result.allEdgesCollisionFree);
  assert.deepEqual(result, runPotentialField(mode));
});
test('episode16 analytic force is the negative potential gradient', () => {
  const p: PFPoint = [.7, .2], h = 1e-5, force = pfForces(p).total;
  for (let i = 0; i < 2; i++) {
    const a: PFPoint = [...p], b: PFPoint = [...p]; a[i] += h; b[i] -= h;
    near((pfPotential(a) - pfPotential(b)) / (2 * h), -force[i], 1e-7);
  }
  assert.throws(() => pfForces(PF_MODEL.obstacles[0]));
});
test('episode16 analytic segment checks reject crossing despite free endpoints', () => {
  assert(!pfEdge([1, .6], [3, .6]));
  assert(pfEdge([0, -2.2], [5, -2.2]));
  assert(!pfEdge([0, 0], [6, 0])); assert(!pfEdge([NaN, 0], [1, 0]));
});
test('episode16 changing parameters remains bounded, deterministic and collision checked', () => {
  for (const attraction of [.2, 1, 3]) for (const repulsion of [.2, 2.144, 5]) {
    const r = runPotentialField('subgoal', { attraction, repulsion, gain: .08 });
    assert(r.iterations <= 2400); assert(r.path.length <= 2401); assert(r.allEdgesCollisionFree);
    if (r.status === 'reached') assert(r.goalDistanceM < .07);
    for (let i = 1; i < r.path.length; i++) assert(pfEdge(r.path[i - 1], r.path[i]));
  }
  const limited = runPotentialField('baseline', { budget: 1 });
  assert.equal(limited.status, 'iteration_budget_exhausted');
  assert.throws(() => runPotentialField('baseline', { budget: 1e9 }));
  assert.throws(() => runPotentialField('baseline', { repulsion: NaN }));
});
test('episode16 accepted steps descend the active potential, not necessarily the original goal potential', () => {
  const r = runPotentialField('subgoal');
  for (let i = 1; i < r.path.length; i++) {
    assert(pfPotential(r.path[i], r.goals[i], r.options) <= pfPotential(r.path[i - 1], r.goals[i], r.options) + 1.1e-10);
  }
  assert(r.events.some(e => e.kind === 'temporary_goals_enabled'));
});
