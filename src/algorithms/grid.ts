import { Heap, distance, type Frame, type Point } from "./core.ts";
export interface GridOptions {
  width: number;
  height: number;
  start: Point;
  goal: Point;
  obstacles: Set<string>;
  weights?: Map<string, number>;
  diagonal: boolean;
  inflation: number;
  heuristicWeight: number;
  algorithm: "dijkstra" | "astar";
}
export const cellKey = (q: Point) => `${q[0]},${q[1]}`;
export function makeGrid(preset = "office", width = 30, height = 22) {
  const walls = new Set<string>();
  if (preset === "maze") {
    for (let x = 5; x < width - 2; x += 5)
      for (let y = 0; y < height; y++)
        if (Math.abs(y - ((x / 5) % 2 ? height - 5 : 4)) > 1)
          walls.add(`${x},${y}`);
  } else {
    for (let x = 10; x <= 12; x++)
      for (let y = 1; y < 17; y++) walls.add(`${x},${y}`);
    for (let x = 19; x <= 22; x++)
      for (let y = 9; y <= 15; y++) walls.add(`${x},${y}`);
    for (let x = 3; x < 7; x++)
      for (let y = 10; y < 13; y++) walls.add(`${x},${y}`);
  }
  return walls;
}
export function inflate(o: Pick<GridOptions, "obstacles" | "inflation">) {
  const out = new Set(o.obstacles);
  for (const k of o.obstacles) {
    const [x, y] = k.split(",").map(Number);
    for (let dx = -o.inflation; dx <= o.inflation; dx++)
      for (let dy = -o.inflation; dy <= o.inflation; dy++)
        if (Math.hypot(dx, dy) <= o.inflation) out.add(`${x + dx},${y + dy}`);
  }
  return out;
}
export function* searchGrid(o: GridOptions): Generator<Frame> {
  const blocked = inflate(o);
  const valid = (p: Point) =>
    p[0] >= 0 &&
    p[0] < o.width &&
    p[1] >= 0 &&
    p[1] < o.height &&
    !blocked.has(cellKey(p));
  const stats = {
    iterations: 0,
    checks: 0,
    expanded: 0,
    cost: null as number | null,
    firstSolution: null as number | null,
    status: "搜索中",
    message: "起点入队，准备比较累计成本",
  };
  const closed = new Map<string, Point>(),
    open = new Map<string, Point>(),
    parent = new Map<string, Point>(),
    g = new Map<string, number>();
  const h = (q: Point) => {
    const dx = Math.abs(q[0] - o.goal[0]),
      dy = Math.abs(q[1] - o.goal[1]);
    return o.algorithm === "dijkstra"
      ? 0
      : o.heuristicWeight *
          (o.diagonal
            ? Math.max(dx, dy) + (Math.SQRT2 - 1) * Math.min(dx, dy)
            : dx + dy);
  };
  const heap = new Heap<{ q: Point; g: number }>();
  let path: Point[] = [];
  const state = (): Frame => ({
    kind: "grid",
    stats: { ...stats },
    path,
    open: [...open.values()],
    closed: [...closed.values()],
    current: undefined,
  });
  if (!valid(o.start) || !valid(o.goal)) {
    stats.status = "起终点不可用";
    stats.message = "起终点落在障碍、膨胀区或地图边界外，请修改配置。";
    yield state();
    return;
  }
  if (
    o.weights &&
    [...o.weights.values()].some((v) => v < 1 || !Number.isFinite(v))
  )
    throw Error("Cell weights must be finite and >= 1");
  g.set(cellKey(o.start), 0);
  open.set(cellKey(o.start), o.start);
  heap.push(h(o.start), { q: o.start, g: 0 });
  const dirs = o.diagonal
    ? [
        [1, 0],
        [-1, 0],
        [0, 1],
        [0, -1],
        [1, 1],
        [1, -1],
        [-1, 1],
        [-1, -1],
      ]
    : [
        [1, 0],
        [-1, 0],
        [0, 1],
        [0, -1],
      ];
  while (heap.size) {
    const item = heap.pop()!.value;
    const q = item.q,
      k = cellKey(q);
    if (item.g !== (g.get(k) ?? Infinity) || closed.has(k)) continue;
    open.delete(k);
    closed.set(k, q);
    stats.iterations++;
    stats.expanded = closed.size;
    if (k === cellKey(o.goal)) {
      let p = q;
      path = [[...p]];
      while (parent.has(cellKey(p))) {
        p = parent.get(cellKey(p))!;
        path.push([...p]);
      }
      path.reverse();
      stats.cost = g.get(k)!;
      stats.firstSolution = stats.iterations;
      stats.status = "已找到路径";
      stats.message =
        o.algorithm === "astar" && o.heuristicWeight > 1
          ? "加权A*：本次不承诺最优；权重调回1后再与Dijkstra对照。"
          : "回溯父节点得到完整路线；当前代价设置下结果最优。";
      yield { ...state(), current: q };
      return;
    }
    for (const [dx, dy] of dirs) {
      const to = [q[0] + dx, q[1] + dy];
      stats.checks++;
      if (!valid(to)) continue;
      if (dx && dy && (!valid([q[0] + dx, q[1]]) || !valid([q[0], q[1] + dy])))
        continue;
      const tk = cellKey(to);
      const cost = item.g + distance(q, to) * (o.weights?.get(tk) ?? 1);
      if (cost < (g.get(tk) ?? Infinity) - 1e-10) {
        g.set(tk, cost);
        parent.set(tk, q);
        closed.delete(tk);
        open.set(tk, to);
        heap.push(cost + h(to), { q: to, g: cost });
      }
    }
    stats.message = `取出 (${q.join(", ")})；g=${item.g.toFixed(2)}，f=${(item.g + h(q)).toFixed(2)}，展开有效邻居。`;
    yield { ...state(), current: q };
  }
  stats.status = "无可行路径";
  stats.message = "可达节点已耗尽。检查障碍、膨胀半径或起终点。";
  yield state();
}
