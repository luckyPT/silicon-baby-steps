import { distance, lerp, type Environment, type Point } from "./core.ts";
export const radians = (x: number) => (x * Math.PI) / 180;
export const degrees = (x: number) => (x * 180) / Math.PI;
export function forward(q: Point): Point[] {
  return [
    [0, 0],
    [Math.cos(q[0]), Math.sin(q[0])],
    [
      Math.cos(q[0]) + Math.cos(q[0] + q[1]),
      Math.sin(q[0]) + Math.sin(q[0] + q[1]),
    ],
  ];
}
export function segmentDistance(p: Point, a: Point, b: Point) {
  const ab = b.map((v, i) => v - a[i]);
  const den = ab.reduce((s, v) => s + v * v, 0);
  const t =
    den === 0
      ? 0
      : Math.max(
          0,
          Math.min(1, ab.reduce((s, v, i) => s + (p[i] - a[i]) * v, 0) / den),
        );
  return distance(p, lerp(a, b, t));
}
export function armEnvironment(obstacleRadius = 0.15): Environment {
  const limit = radians(150);
  const clear = (q: Point) => {
    if (q.some((x) => Math.abs(x) > limit + 1e-8)) return -1;
    const p = forward(q);
    return (
      Math.min(
        segmentDistance([0.9, 0.5], p[0], p[1]),
        segmentDistance([0.9, 0.5], p[1], p[2]),
      ) -
      obstacleRadius -
      0.05
    );
  };
  return {
    kind: "arm",
    bounds: [
      [-limit, limit],
      [-limit, limit],
    ],
    start: [radians(-30), radians(90)],
    goal: [radians(-30), radians(150)],
    clearance: clear,
    edge(a, b) {
      const n = Math.max(1, Math.ceil(distance(a, b) / radians(0.5)));
      const bound = (2 * Math.abs(b[0] - a[0]) + Math.abs(b[1] - a[1])) / n;
      let min = Infinity;
      for (let j = 0; j <= n; j++) {
        min = Math.min(min, clear(lerp(a, b, j / n)));
        if (min <= 0) return false;
      }
      return min - bound > 0;
    },
  };
}
export const boxes = [
  { center: [0, 1.5, 0], size: [0.65, 2.2, 2.0] },
  { center: [-1.55, 0.7, -0.8], size: [0.85, 1.4, 0.85] },
  { center: [1.4, 2.35, 1.1], size: [0.85, 1.0, 1.0] },
];
export function spaceEnvironment(padding = 0.12): Environment {
  const bounds: [number, number][] = [
    [-3.2, 3.2],
    [0.25, 3.5],
    [-3.2, 3.2],
  ];
  const clear = (p: Point) => {
    let c = Infinity;
    for (let i = 0; i < 3; i++)
      c = Math.min(c, p[i] - bounds[i][0], bounds[i][1] - p[i]);
    for (const b of boxes) {
      const d = p.map((v, i) => Math.abs(v - b.center[i]) - b.size[i] / 2);
      const sd =
        Math.hypot(...d.map((v) => Math.max(0, v))) +
        Math.min(Math.max(...d), 0) -
        padding;
      c = Math.min(c, sd);
    }
    return c;
  };
  return {
    kind: "space",
    bounds,
    start: [-2.6, 0.65, -2.5],
    goal: [2.6, 2.9, 2.5],
    clearance: clear,
    edge(a, b) {
      const n = Math.max(1, Math.ceil(distance(a, b) / 0.045));
      let min = Infinity;
      for (let j = 0; j <= n; j++) {
        min = Math.min(min, clear(lerp(a, b, j / n)));
        if (min <= 0) return false;
      }
      return min - distance(a, b) / n > 0;
    },
  };
}
