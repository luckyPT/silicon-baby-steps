import test from "node:test";
import assert from "node:assert/strict";
import {
  distance,
  pathCost,
  trace,
  type Frame,
} from "../src/algorithms/core.ts";
import {
  makeGrid,
  searchGrid,
  type GridOptions,
} from "../src/algorithms/grid.ts";
import {
  armEnvironment,
  spaceEnvironment,
  radians,
  forward,
} from "../src/algorithms/environments.ts";
import { samplePlan } from "../src/algorithms/sampling.ts";
import { trapezoid, trajectoryPlan } from "../src/algorithms/trajectory.ts";
import { dwaPlan, obstaclesAt } from "../src/algorithms/dwa.ts";
const last = (g: Generator<Frame>) => {
  let f: Frame | undefined;
  for (const x of g) f = x;
  return f!;
};
test("Dijkstra and admissible A* agree on weighted route cost with no diagonal corner cutting", () => {
  const o: GridOptions = {
    width: 30,
    height: 22,
    start: [2, 3],
    goal: [27, 18],
    obstacles: makeGrid(),
    weights: new Map(Array.from({ length: 15 }, (_, i) => [`17,${i + 2}`, 4])),
    diagonal: true,
    inflation: 0,
    heuristicWeight: 1,
    algorithm: "dijkstra",
  };
  const a = last(searchGrid(o)),
    b = last(searchGrid({ ...o, algorithm: "astar" }));
  assert.ok(a.path.length > 1);
  assert.ok(Math.abs(a.stats.cost! - b.stats.cost!) < 1e-8);
  assert.ok(b.stats.iterations < a.stats.iterations);
  for (const p of [a.path, b.path])
    for (let i = 1; i < p.length; i++) {
      const [x, y] = p[i],
        [px, py] = p[i - 1];
      if (x !== px && y !== py) {
        assert.ok(!o.obstacles.has(`${x},${py}`));
        assert.ok(!o.obstacles.has(`${px},${y}`));
      }
    }
});
test("unreachable and inflated blocked endpoints terminate explicitly", () => {
  const base: GridOptions = {
    width: 5,
    height: 5,
    start: [0, 0],
    goal: [4, 4],
    obstacles: new Set(["1,0", "0,1"]),
    diagonal: true,
    inflation: 0,
    heuristicWeight: 1,
    algorithm: "astar",
  };
  assert.equal(last(searchGrid(base)).stats.status, "无可行路径");
  assert.equal(
    last(searchGrid({ ...base, inflation: 1 })).stats.status,
    "起终点不可用",
  );
});
test("arm kinematics and whole-edge collision reject unsafe direct connection with safe endpoints", () => {
  const env = armEnvironment();
  assert.ok(env.clearance(env.start) > 0);
  assert.ok(env.clearance(env.goal) > 0);
  assert.ok(env.clearance([radians(-30), radians(120)]) < 0);
  assert.equal(env.edge(env.start, env.goal), false);
  assert.ok(
    Math.abs(distance(forward(env.start)[0], forward(env.start)[1]) - 1) <
      1e-12,
  );
});
for (const kind of ["arm", "space"] as const)
  for (const algorithm of ["rrt", "connect", "star"] as const)
    test(`${algorithm} in ${kind}: reproducible safe raw path, consistent costs and acyclic tree`, () => {
      const env = kind === "arm" ? armEnvironment() : spaceEnvironment();
      const options = {
        algorithm,
        env,
        seed: 7,
        iterations: 1000,
        step: kind === "arm" ? radians(10) : 0.45,
        radius: kind === "arm" ? radians(35) : 1.25,
        goalBias: 0.08,
      };
      let previous = Infinity,
        rewires = 0;
      const g = samplePlan(options);
      let result: Frame | undefined;
      for (const f of g) {
        result = f;
        if (f.stats.cost !== null) {
          assert.ok(f.stats.cost <= previous + 1e-8);
          previous = f.stats.cost;
          assert.ok(Math.abs(pathCost(f.path) - f.stats.cost) < 1e-7);
        }
        if (algorithm === "star" && f.stats.iterations % 50 === 0) {
          rewires += (f.rewired ?? []).length;
          for (let i = 0; i < f.nodes!.length; i++) {
            const path = trace(f.nodes!, f.parents!, i);
            assert.ok(Math.abs(pathCost(path) - f.costs![i]) < 1e-7);
          }
        }
      }
      assert.ok(
        result!.path.length > 1,
        `${algorithm}/${kind} did not find a path`,
      );
      assert.ok(distance(result!.path[0], env.start) < 1e-9);
      assert.ok(distance(result!.path.at(-1)!, env.goal) < 1e-9);
      for (let i = 1; i < result!.path.length; i++)
        assert.ok(env.edge(result!.path[i - 1], result!.path[i]));
      const again = last(samplePlan(options));
      assert.deepEqual(result!.path, again.path);
      assert.equal(result!.stats.checks, again.stats.checks);
    });
test("limited acceleration reference takes 10.5 seconds and respects velocity bounds", () => {
  const p = trapezoid(2, 1, 0.5);
  assert.equal(p.duration, 4);
  const g = trajectoryPlan({
    mode: "limited",
    maxSpeed: 1,
    acceleration: 0.5,
    maxOmega: Math.PI / 4,
    angularAcceleration: Math.PI / 2,
  });
  let lastFrame;
  for (const f of g) lastFrame = f;
  assert.equal(lastFrame!.stats.iterations, 210);
  assert.ok(distance(lastFrame!.robot!.slice(0, 2), [4, 4]) < 1e-8);
  assert.equal(lastFrame!.stats.cost, 4);
});
test("DWA executed steps remain outside static and predicted moving obstacles", () => {
  const g = dwaPlan({
    dynamic: true,
    guided: false,
    maxSpeed: 1.4,
    horizon: 2.4,
    clearanceWeight: 0.5,
    steps: 100,
  });
  let n = 0;
  for (const f of g) {
    n++;
    const q = f.robot!;
    for (const ob of obstaclesAt(f.stats.iterations * 0.15, true))
      assert.ok(distance(q.slice(0, 2), ob.p) > ob.r + 0.28 - 1e-8);
    if (f.chosen) assert.ok(f.trajectories!.length > 0);
  }
  assert.equal(n, 100);
});
