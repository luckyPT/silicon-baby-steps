import { clamp, distance, type Point, type Frame } from "./core.ts";
export interface Obstacle {
  p: Point;
  r: number;
}
export const staticObstacles: Obstacle[] = [
  { p: [6, 5], r: 0.8 },
  { p: [9, 9], r: 0.8 },
  { p: [13, 7], r: 0.8 },
  { p: [14, 3], r: 0.8 },
];
export const dynamicObstacle = (t: number): Obstacle => ({
  p: [10, 4.0 + 2.0 * Math.sin(t * 0.45)],
  r: 0.45,
});
export const obstaclesAt = (t: number, dynamic: boolean) =>
  dynamic ? [...staticObstacles, dynamicObstacle(t)] : staticObstacles;
export interface DwaOptions {
  dynamic: boolean;
  guided: boolean;
  maxSpeed: number;
  horizon: number;
  clearanceWeight: number;
  steps: number;
}
export function rollout(q: Point, v: number, w: number, dt: number, n: number) {
  const out: Point[] = [[...q]];
  let p = [...q];
  for (let i = 0; i < n; i++) {
    const next = [
      p[0] + v * Math.cos(p[2] + (w * dt) / 2) * dt,
      p[1] + v * Math.sin(p[2] + (w * dt) / 2) * dt,
      p[2] + w * dt,
    ];
    out.push(next);
    p = next;
  }
  return out;
}
export function* dwaPlan(o: DwaOptions): Generator<Frame> {
  let q = [2, 2, 0.3],
    v = 0,
    w = 0,
    checks = 0;
  const goal = [17, 11],
    dt = 0.15,
    acc = 0.9,
    wAcc = 2.2;
  const route: Point[] = [
    [2, 2],
    [5, 2.5],
    [8, 3],
    [10, 7],
    [12, 10],
    [17, 11],
  ];
  const travelled: Point[] = [[...q]];
  for (let it = 1; it <= o.steps; it++) {
    const now = (it - 1) * dt;
    let target = goal;
    if (o.guided) {
      let near = 0,
        best = Infinity;
      route.forEach((p, i) => {
        const d = distance(q.slice(0, 2), p);
        if (d < best) {
          best = d;
          near = i;
        }
      });
      target = route[Math.min(route.length - 1, near + 1)];
    }
    const trajectories: Point[][] = [];
    let chosen: Point[] | undefined,
      score = -Infinity,
      bv = 0,
      bw = 0;
    for (let iv = 0; iv <= 6; iv++)
      for (let iw = 0; iw <= 16; iw++) {
        const nv =
          clamp(v - acc * dt, 0, o.maxSpeed) +
          ((clamp(v + acc * dt, 0, o.maxSpeed) -
            clamp(v - acc * dt, 0, o.maxSpeed)) *
            iv) /
            6;
        const nw =
          clamp(w - wAcc * dt, -1.6, 1.6) +
          ((clamp(w + wAcc * dt, -1.6, 1.6) - clamp(w - wAcc * dt, -1.6, 1.6)) *
            iw) /
            16;
        const n = Math.ceil(o.horizon / dt),
          path = rollout(q, nv, nw, dt, n);
        checks++;
        let min = Infinity,
          safe = true;
        for (let k = 0; k < path.length; k++) {
          const p = path[k];
          min = Math.min(
            min,
            p[0] - 0.28,
            19.5 - p[0] - 0.28,
            p[1] - 0.28,
            13.5 - p[1] - 0.28,
          );
          for (const ob of obstaclesAt(now + k * dt, o.dynamic))
            min = Math.min(min, distance(p.slice(0, 2), ob.p) - ob.r - 0.28);
          if (min <= nv * dt + 0.04) {
            safe = false;
            break;
          }
        }
        if (!safe || min < (nv * nv) / (2 * acc)) continue;
        trajectories.push(path);
        const end = path.at(-1)!;
        const angle = Math.atan2(target[1] - end[1], target[0] - end[0]);
        const heading = Math.cos(angle - end[2]);
        const value =
          -1.8 * distance(end.slice(0, 2), target) +
          1.3 * heading +
          0.55 * nv +
          o.clearanceWeight * Math.min(min, 1.2) -
          0.03 * Math.abs(nw);
        if (value > score) {
          score = value;
          chosen = path;
          bv = nv;
          bw = nw;
        }
      }
    const had = !!chosen;
    if (chosen) {
      q = chosen[1];
      v = bv;
      w = bw;
      travelled.push([...q]);
    } else {
      v = 0;
      w = 0;
    }
    const done = distance(q.slice(0, 2), goal) < 0.5;
    yield {
      kind: "dwa",
      robot: [...q],
      current: [...q],
      target,
      trajectories,
      chosen,
      path: travelled,
      route: o.guided ? route : undefined,
      stats: {
        iterations: it,
        checks,
        expanded: trajectories.length,
        cost: travelled
          .slice(1)
          .reduce(
            (s, p, i) => s + distance(p.slice(0, 2), travelled[i].slice(0, 2)),
            0,
          ),
        firstSolution: done ? it : null,
        status: done ? "已到达" : had ? "滚动规划中" : "安全停车",
        message: done
          ? "到达目标区域；当前实验是几何与简化运动学仿真。"
          : had
            ? `动态窗口选中 v=${v.toFixed(2)} m/s，ω=${w.toFixed(2)} rad/s；只执行预测轨迹的第一小段。`
            : "当前窗口无通过安全筛选的轨迹，停车后继续观察；可增加预测时域或开启路线引导。",
      },
    };
    if (done) return;
  }
}
