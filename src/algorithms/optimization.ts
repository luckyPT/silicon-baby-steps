/** Episode 18: finite point-robot CHOMP/STOMP mechanisms, not full robot planners.
 * Port of experiments/original/18/experiment.py. Browser STOMP uses Mulberry32
 * and Box–Muller rather than NumPy PCG64: same seed is reproducible here, not
 * numerically identical to the Python video's random stream.
 */
import { random } from './core.ts';
import { optimizationInitialVertices } from './optimization-data.ts';
export type XY = [number, number];
export interface Disc { center: XY; radius: number }
export type OptimizationMethod = 'chomp' | 'stomp';
export type OptimizationScene = 'route' | 'symmetry';
export const optimizationDiscs: Disc[] = [
  { center: [1.6, -.65], radius: .45 },
  { center: [2.55, .75], radius: .5 },
  { center: [3.65, -.55], radius: .45 },
];
const N = 41, M = N - 2, EPS = .30, WOBS = 35;
const U = [.046910077030668, .2307653449471585, .5, .7692346550528415, .953089922969332];
const W = [.1184634425280945, .239314335249683, .2844444444444445, .239314335249683, .1184634425280945];
const zero = (): XY => [0, 0];
const copy = (p: XY[]) => p.map(q => [...q] as XY);
export function resampleOptimizationPath(p: XY[], count = N): XY[] {
  const distances = [0];
  for (let i = 1; i < p.length; i++) distances.push(distances[i - 1] + Math.hypot(p[i][0] - p[i - 1][0], p[i][1] - p[i - 1][1]));
  if (p.length < 2 || distances.at(-1)! <= 0 || !Number.isInteger(count) || count < 3) throw Error('Invalid path or sample count');
  let segment = 0;
  return Array.from({ length: count }, (_, i) => {
    const s = distances.at(-1)! * i / (count - 1);
    while (segment < p.length - 2 && distances[segment + 1] < s) segment++;
    const t = (s - distances[segment]) / (distances[segment + 1] - distances[segment]);
    return [p[segment][0] * (1 - t) + p[segment + 1][0] * t, p[segment][1] * (1 - t) + p[segment + 1][1] * t];
  });
}
export function optimizationProblem(scene: OptimizationScene = 'route') {
  return scene === 'symmetry'
    ? { initial: Array.from({ length: N }, (_, i) => [5 * i / (N - 1), 0] as XY), discs: [{ center: [2.5, 0] as XY, radius: .65 }] }
    : { initial: resampleOptimizationPath(optimizationInitialVertices), discs: optimizationDiscs.map(d => ({ center: [...d.center] as XY, radius: d.radius })) };
}
function potential(q: XY, discs: Disc[]) {
  let distance = Infinity, grad: XY = [0, 0];
  for (const disc of discs) {
    const dx = q[0] - disc.center[0], dy = q[1] - disc.center[1], r = Math.hypot(dx, dy), d = r - disc.radius;
    if (d < distance) { distance = d; grad = [dx / Math.max(1e-12, r), dy / Math.max(1e-12, r)]; }
  }
  const c = distance < 0 ? -distance + EPS / 2 : distance < EPS ? (distance - EPS) ** 2 / (2 * EPS) : 0;
  const cp = distance < 0 ? -1 : distance < EPS ? (distance - EPS) / EPS : 0;
  return { c, gradient: [cp * grad[0], cp * grad[1]] as XY };
}
export function optimizationCost(p: XY[], discs = optimizationDiscs, gradient = false) {
  let smooth = 0, obstacle = 0;
  const stage = new Array<number>(p.length).fill(0), g = p.map(zero);
  for (let i = 0; i < p.length - 2; i++) for (let dim = 0; dim < 2; dim++) {
    const dd = p[i][dim] - 2 * p[i + 1][dim] + p[i + 2][dim];
    smooth += .5 * dd * dd;
    if (gradient) { g[i][dim] += dd; g[i + 1][dim] -= 2 * dd; g[i + 2][dim] += dd; }
  }
  for (let i = 0; i < p.length - 1; i++) {
    const d: XY = [p[i + 1][0] - p[i][0], p[i + 1][1] - p[i][1]], length = Math.hypot(...d);
    let avg = 0;
    const ga: XY = [0, 0], gb: XY = [0, 0];
    for (let j = 0; j < U.length; j++) {
      const value = potential([p[i][0] + U[j] * d[0], p[i][1] + U[j] * d[1]], discs);
      avg += W[j] * value.c;
      if (gradient) for (let dim = 0; dim < 2; dim++) {
        ga[dim] += W[j] * (1 - U[j]) * value.gradient[dim];
        gb[dim] += W[j] * U[j] * value.gradient[dim];
      }
    }
    const edge = length * avg;
    obstacle += edge; stage[i] += .5 * WOBS * edge; stage[i + 1] += .5 * WOBS * edge;
    if (gradient) for (let dim = 0; dim < 2; dim++) {
      const v = d[dim] / Math.max(1e-12, length);
      g[i][dim] += WOBS * (-v * avg + length * ga[dim]);
      g[i + 1][dim] += WOBS * (v * avg + length * gb[dim]);
    }
  }
  return { cost: smooth + WOBS * obstacle, smooth, obstacle, stage, gradient: g };
}
/** Exact minimum clearance for every straight segment against every disc. */
export function optimizationClearance(p: XY[], discs = optimizationDiscs) {
  let best = Infinity;
  for (let i = 0; i < p.length - 1; i++) {
    const a = p[i], d: XY = [p[i + 1][0] - a[0], p[i + 1][1] - a[1]], squared = d[0] ** 2 + d[1] ** 2;
    for (const disc of discs) {
      const t = Math.min(1, Math.max(0, ((disc.center[0] - a[0]) * d[0] + (disc.center[1] - a[1]) * d[1]) / Math.max(1e-15, squared)));
      best = Math.min(best, Math.hypot(a[0] + t * d[0] - disc.center[0], a[1] + t * d[1] - disc.center[1]) - disc.radius);
    }
  }
  return best;
}
export function optimizationMetrics(p: XY[], discs = optimizationDiscs) {
  const { cost, smooth, obstacle } = optimizationCost(p, discs), clearance = optimizationClearance(p, discs);
  let length = 0;
  for (let i = 1; i < p.length; i++) length += Math.hypot(p[i][0] - p[i - 1][0], p[i][1] - p[i - 1][1]);
  return { cost, smooth, obstacle, length, clearance, collisionFree: clearance > 1e-6 };
}
function cholesky(a: number[][]) {
  const n = a.length, l = Array.from({ length: n }, () => new Array<number>(n).fill(0));
  for (let i = 0; i < n; i++) for (let j = 0; j <= i; j++) {
    let s = a[i][j];
    for (let k = 0; k < j; k++) s -= l[i][k] * l[j][k];
    if (i === j && s <= 0) throw Error('Metric is not positive definite');
    l[i][j] = i === j ? Math.sqrt(s) : s / l[j][j];
  }
  return l;
}
let cachedMetric: { inverse: number[][]; smoother: number[][]; noise: number[][] } | undefined;
function metric() {
  if (cachedMetric) return cachedMetric;
  const d = Array.from({ length: M }, (_, i) => Array.from({ length: M }, (_, j) => i === j ? -2 : Math.abs(i - j) === 1 ? 1 : 0));
  const a = Array.from({ length: M }, (_, i) => Array.from({ length: M }, (_, j) => d.reduce((sum, row) => sum + row[i] * row[j], 0)));
  const l = cholesky(a), inverse = Array.from({ length: M }, () => new Array<number>(M).fill(0));
  for (let col = 0; col < M; col++) {
    const y = new Array<number>(M).fill(0), x = new Array<number>(M).fill(0);
    for (let i = 0; i < M; i++) { let s = i === col ? 1 : 0; for (let j = 0; j < i; j++) s -= l[i][j] * y[j]; y[i] = s / l[i][i]; }
    for (let i = M - 1; i >= 0; i--) { let s = y[i]; for (let j = i + 1; j < M; j++) s -= l[j][i] * x[j]; x[i] = s / l[i][i]; }
    x.forEach((value, row) => { inverse[row][col] = value; });
  }
  for (let i = 0; i < M; i++) for (let j = 0; j < i; j++) inverse[i][j] = inverse[j][i] = (inverse[i][j] + inverse[j][i]) / 2;
  const maxDiag = Math.max(...inverse.map((row, i) => row[i])), maxima = Array.from({ length: M }, (_, j) => Math.max(...inverse.map(row => row[j])));
  return cachedMetric = { inverse, smoother: inverse.map(row => row.map((v, j) => v / (M * maxima[j]))), noise: cholesky(inverse.map(row => row.map(v => v / maxDiag))) };
}
function multiply(a: number[][], p: XY[]): XY[] {
  return a.map(row => row.reduce<XY>((sum, value, j) => [sum[0] + value * p[j][0], sum[1] + value * p[j][1]], [0, 0]));
}
export interface OptimizationOptions { method: OptimizationMethod; scene?: OptimizationScene; seed?: number; iterations?: number; sigma?: number }
export interface OptimizationFrame extends ReturnType<typeof optimizationMetrics> {
  iteration: number; path: XY[]; accepted: boolean; stalled: boolean; evaluations: number;
}
export function* optimizeTrajectory(options: OptimizationOptions): Generator<OptimizationFrame> {
  const { method, scene = 'route', seed = 7, iterations = 140, sigma = .30 } = options;
  if (!['chomp', 'stomp'].includes(method) || !['route', 'symmetry'].includes(scene) || !Number.isInteger(iterations) || iterations < 0 || iterations > 500 || !Number.isFinite(seed) || !Number.isFinite(sigma) || sigma <= 0 || sigma > 2) throw Error('Invalid optimization parameters');
  const { initial, discs } = optimizationProblem(scene), { inverse, smoother, noise } = metric(), rng = random(seed);
  const normal = () => Math.sqrt(-2 * Math.log(Math.max(1e-15, rng()))) * Math.cos(2 * Math.PI * rng());
  let p = copy(initial), evaluations = 0, accepted = false, stalled = false;
  for (let iteration = 0; iteration <= iterations; iteration++) {
    yield { iteration, path: copy(p), ...optimizationMetrics(p, discs), accepted, stalled, evaluations };
    if (iteration === iterations || stalled) return;
    let direction: XY[], sign: number, attempts: number;
    const current = optimizationCost(p, discs, method === 'chomp'); evaluations++;
    if (method === 'chomp') {
      direction = multiply(inverse, current.gradient.slice(1, -1));
      const max = Math.max(...direction.map(q => Math.hypot(...q))), scale = Math.min(1, .16 / Math.max(1e-12, max));
      direction = direction.map(q => [q[0] * scale, q[1] * scale]); sign = -1; attempts = 16;
    } else {
      const rollouts = Array.from({ length: 32 }, () => {
        const normals = Array.from({ length: M }, () => [normal(), normal()] as XY);
        const delta = multiply(noise, normals).map(q => [q[0] * sigma, q[1] * sigma] as XY), candidate = copy(p);
        delta.forEach((q, i) => { candidate[i + 1][0] += q[0]; candidate[i + 1][1] += q[1]; });
        evaluations++;
        return { delta, stage: optimizationCost(candidate, discs).stage };
      });
      const raw: XY[] = Array.from({ length: M }, (_, i) => {
        const values = rollouts.map(r => r.stage[i + 1]), lo = Math.min(...values), span = Math.max(...values) - lo;
        const weights = values.map(v => Math.exp(-10 * (span > 1e-12 ? (v - lo) / span : 0))), sum = weights.reduce((a, b) => a + b, 0);
        return rollouts.reduce<XY>((q, r, k) => [q[0] + weights[k] / sum * r.delta[i][0], q[1] + weights[k] / sum * r.delta[i][1]], [0, 0]);
      });
      direction = multiply(smoother, raw); sign = 1; attempts = 10;
    }
    accepted = false;
    for (let attempt = 0; attempt < attempts; attempt++) {
      const alpha = 2 ** -attempt, candidate = copy(p);
      direction.forEach((q, i) => { candidate[i + 1][0] += sign * alpha * q[0]; candidate[i + 1][1] += sign * alpha * q[1]; });
      evaluations++;
      if (optimizationCost(candidate, discs).cost < current.cost - 1e-12) { p = candidate; accepted = true; break; }
    }
    stalled = method === 'chomp' && !accepted;
  }
}
