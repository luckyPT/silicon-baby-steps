import { random } from './core.ts';

export type RoadmapPoint = [number, number];
export type RoadmapEdge = [number, number];
export const roadmapObstacles = [
  { center: [1.6, -.65] as RoadmapPoint, radius: .45 },
  { center: [2.55, .75] as RoadmapPoint, radius: .5 },
  { center: [3.65, -.55] as RoadmapPoint, radius: .45 },
];
export const roadmapQueries: [RoadmapPoint, RoadmapPoint][] = [
  [[0, -1.7], [5, 1.5]], [[0, 1.7], [5, -1.7]], [[0, 0], [5, 0]],
];
const distance = (a: RoadmapPoint, b: RoadmapPoint) => Math.hypot(a[0] - b[0], a[1] - b[1]);
const edgeKey = (a: number, b: number) => a < b ? `${a},${b}` : `${b},${a}`;
export function roadmapPointValid(p: RoadmapPoint) {
  return p.every(Number.isFinite) && p[0] >= -.4 && p[0] <= 5.5 && p[1] >= -2.5 && p[1] <= 2.5 &&
    roadmapObstacles.every(o => distance(p, o.center) > o.radius);
}
export function roadmapEdgeValid(a: RoadmapPoint, b: RoadmapPoint) {
  if (!roadmapPointValid(a) || !roadmapPointValid(b)) return false;
  const dx = b[0] - a[0], dy = b[1] - a[1], norm2 = dx * dx + dy * dy;
  return roadmapObstacles.every(o => {
    const t = Math.max(0, Math.min(1, ((o.center[0] - a[0]) * dx + (o.center[1] - a[1]) * dy) / Math.max(norm2, 1e-15)));
    return Math.hypot(o.center[0] - a[0] - t * dx, o.center[1] - a[1] - t * dy) - o.radius > 1e-8;
  });
}
export interface RoadmapGraph { vertices: RoadmapPoint[]; edges: RoadmapEdge[]; sampleAttempts: number; k: number }
export function buildRoadmap(seed = 17, n = 180, k = 10): RoadmapGraph {
  if (!Number.isInteger(seed) || !Number.isInteger(n) || n < 2 || n > 500 || !Number.isInteger(k) || k < 1 || k >= n)
    throw new Error('Require an integer seed, 2–500 vertices and 1 ≤ k < N.');
  const rng = random(seed), vertices: RoadmapPoint[] = [], edges = new Map<string, RoadmapEdge>();
  let sampleAttempts = 0;
  while (vertices.length < n && sampleAttempts < n * 100) {
    sampleAttempts++;
    const p: RoadmapPoint = [-.4 + 5.9 * rng(), -2.5 + 5 * rng()];
    if (roadmapPointValid(p)) vertices.push(p);
  }
  if (vertices.length !== n) throw new Error('Sampling budget exhausted.');
  for (let i = 0; i < n; i++) {
    const near = vertices.map((p, j) => ({ j, d: distance(vertices[i], p) })).filter(x => x.j !== i).sort((a, b) => a.d - b.d || a.j - b.j).slice(0, k);
    for (const { j } of near) edges.set(edgeKey(i, j), i < j ? [i, j] : [j, i]);
  }
  return { vertices, edges: [...edges.values()].sort((a, b) => a[0] - b[0] || a[1] - b[1]), sampleAttempts, k };
}
export function shortestRoadmapPath(vertices: RoadmapPoint[], edges: RoadmapEdge[], status: Map<string, boolean>, start: number, goal: number) {
  const adjacency: { node: number; cost: number }[][] = vertices.map(() => []);
  for (const [a, b] of edges) if (status.get(edgeKey(a, b)) !== false) {
    const cost = distance(vertices[a], vertices[b]);
    adjacency[a].push({ node: b, cost }); adjacency[b].push({ node: a, cost });
  }
  const costs = vertices.map(() => Infinity), parents = vertices.map(() => -1), done = new Set<number>();
  costs[start] = 0;
  while (true) {
    let current = -1;
    for (let i = 0; i < vertices.length; i++) if (!done.has(i) && Number.isFinite(costs[i]) && (current < 0 || costs[i] < costs[current])) current = i;
    if (current < 0 || current === goal) break;
    done.add(current);
    for (const { node, cost } of adjacency[current]) if (costs[current] + cost < costs[node] - 1e-12) {
      costs[node] = costs[current] + cost; parents[node] = current;
    }
  }
  if (!Number.isFinite(costs[goal])) return { path: [] as number[], cost: null };
  const path: number[] = [];
  for (let node = goal; node >= 0; node = parents[node]) path.push(node);
  return { path: path.reverse(), cost: costs[goal] };
}
export interface RoadmapTrace { candidate: number[]; candidateCost: number | null; tested: { edge: RoadmapEdge; valid: boolean }[]; invalid: RoadmapEdge | null }
export interface RoadmapQueryResult {
  vertices: RoadmapPoint[]; edges: RoadmapEdge[]; eagerPath: number[]; lazyPath: number[];
  eagerCost: number | null; lazyCost: number | null; eagerChecks: number; lazyChecks: number;
  lazySearches: number; trace: RoadmapTrace[]; initialKnownEdges: { edge: RoadmapEdge; valid: boolean }[];
  allReturnedSegmentsCollisionFree: boolean;
}
export function compareRoadmaps(options: { seed?: number; n?: number; k?: number } = {}) {
  const seed = options.seed ?? 17, n = options.n ?? 180, k = options.k ?? 10, graph = buildRoadmap(seed, n, k);
  const eagerCache = new Map<string, boolean>(), lazyCache = new Map<string, boolean>();
  for (const [a, b] of graph.edges) eagerCache.set(edgeKey(a, b), roadmapEdgeValid(graph.vertices[a], graph.vertices[b]));
  const queries: RoadmapQueryResult[] = [];
  for (const [start, goal] of roadmapQueries) {
    const vertices = [...graph.vertices, start, goal], edges = [...graph.edges], attachment: RoadmapEdge[] = [];
    for (const i of [n, n + 1]) {
      const nearest = graph.vertices.map((p, j) => ({ j, d: distance(p, vertices[i]) })).sort((a, b) => a.d - b.d || a.j - b.j).slice(0, k);
      for (const { j } of nearest) attachment.push([j, i]);
    }
    edges.push(...attachment);
    const eager = new Map(eagerCache), lazy = new Map(lazyCache), initialKnownEdges = [...lazy].map(([key, valid]) => ({ edge: key.split(',').map(Number) as RoadmapEdge, valid }));
    for (const [a, b] of attachment) eager.set(edgeKey(a, b), roadmapEdgeValid(vertices[a], vertices[b]));
    const eagerResult = shortestRoadmapPath(vertices, edges, eager, n, n + 1), trace: RoadmapTrace[] = [];
    let lazyResult = { path: [] as number[], cost: null as number | null }, lazyChecks = 0, lazySearches = 0;
    // Every failed search removes at least one edge, hence this is bounded.
    for (let pass = 0; pass <= edges.length; pass++) {
      lazySearches++; lazyResult = shortestRoadmapPath(vertices, edges, lazy, n, n + 1);
      const event: RoadmapTrace = { candidate: [...lazyResult.path], candidateCost: lazyResult.cost, tested: [], invalid: null };
      for (let j = 1; j < lazyResult.path.length; j++) {
        const a = lazyResult.path[j - 1], b = lazyResult.path[j], key = edgeKey(a, b), edge: RoadmapEdge = a < b ? [a, b] : [b, a];
        if (!lazy.has(key)) {
          const valid = roadmapEdgeValid(vertices[a], vertices[b]); lazy.set(key, valid); lazyChecks++; event.tested.push({ edge, valid });
          if (!valid) { event.invalid = edge; break; }
        }
      }
      trace.push(event);
      if (!event.invalid) break;
    }
    for (const [key, valid] of lazy) if (key.split(',').every(x => Number(x) < n)) lazyCache.set(key, valid);
    const safe = [eagerResult.path, lazyResult.path].every(path => path.slice(1).every((b, j) => roadmapEdgeValid(vertices[path[j]], vertices[b])));
    queries.push({ vertices, edges, eagerPath: eagerResult.path, lazyPath: lazyResult.path, eagerCost: eagerResult.cost, lazyCost: lazyResult.cost, eagerChecks: attachment.length, lazyChecks, lazySearches, trace, initialKnownEdges, allReturnedSegmentsCollisionFree: safe });
  }
  return { seed, n, k, graph, queries, eagerBaseChecks: graph.edges.length, eagerTotalChecks: graph.edges.length + queries.reduce((a, q) => a + q.eagerChecks, 0), lazyTotalChecks: queries.reduce((a, q) => a + q.lazyChecks, 0), randomGenerator: 'Browser mulberry32; not NumPy PCG64', scope: 'Static 2D point robot; inflated disks. Only edges are lazy. Counts segment collision calls, not runtime.' };
}
