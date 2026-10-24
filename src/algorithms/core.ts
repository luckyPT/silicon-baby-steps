export type Point = number[];
export const distance = (a: Point, b: Point) =>
  Math.hypot(...a.map((v, i) => v - b[i]));
export const lerp = (a: Point, b: Point, t: number) =>
  a.map((v, i) => v + (b[i] - v) * t);
export const clamp = (x: number, a: number, b: number) =>
  Math.min(b, Math.max(a, x));
export function random(seed: number) {
  let a = seed >>> 0;
  return () => {
    a += 0x6d2b79f5;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
export class Heap<T> {
  data: { key: number; value: T }[] = [];
  push(key: number, value: T) {
    const a = this.data;
    let i = a.length;
    a.push({ key, value });
    while (i > 0) {
      const p = (i - 1) >> 1;
      if (a[p].key <= key) break;
      [a[i], a[p]] = [a[p], a[i]];
      i = p;
    }
  }
  pop() {
    const a = this.data;
    if (!a.length) return undefined;
    const out = a[0];
    const last = a.pop()!;
    if (a.length) {
      a[0] = last;
      let i = 0;
      for (;;) {
        let j = i,
          l = i * 2 + 1,
          r = l + 1;
        if (l < a.length && a[l].key < a[j].key) j = l;
        if (r < a.length && a[r].key < a[j].key) j = r;
        if (j === i) break;
        [a[i], a[j]] = [a[j], a[i]];
        i = j;
      }
    }
    return out;
  }
  get size() {
    return this.data.length;
  }
}
export interface Stats {
  iterations: number;
  checks: number;
  expanded: number;
  cost: number | null;
  firstSolution: number | null;
  status: string;
  message: string;
}
export interface Frame {
  kind: "grid" | "sampling" | "dwa";
  stats: Stats;
  path: Point[];
  informedBound?: number;
  nodes?: Point[];
  parents?: number[];
  costs?: number[];
  secondNodes?: Point[];
  secondParents?: number[];
  open?: Point[];
  closed?: Point[];
  current?: Point;
  target?: Point;
  candidate?: Point;
  accepted?: boolean;
  rewired?: number[];
  trajectories?: Point[][];
  chosen?: Point[];
  robot?: Point;
  route?: Point[];
}
export interface Environment {
  kind: "arm" | "space";
  bounds: [number, number][];
  start: Point;
  goal: Point;
  clearance(q: Point): number;
  edge(a: Point, b: Point): boolean;
}
export const pathCost = (p: Point[]) =>
  p.slice(1).reduce((s, q, i) => s + distance(p[i], q), 0);
export function trace(nodes: Point[], parents: number[], i: number) {
  const path: Point[] = [];
  const seen = new Set<number>();
  while (i >= 0) {
    if (seen.has(i)) throw Error("Parent cycle");
    seen.add(i);
    path.push([...nodes[i]]);
    i = parents[i];
  }
  return path.reverse();
}
