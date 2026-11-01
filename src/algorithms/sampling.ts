import {
  distance,
  lerp,
  random,
  trace,
  pathCost,
  type Point,
  type Frame,
  type Environment,
} from "./core.ts";
export interface SamplingOptions {
  algorithm: "rrt" | "connect" | "star";
  env: Environment;
  seed: number;
  iterations: number;
  step: number;
  radius: number;
  goalBias: number;
}
const steer = (a: Point, b: Point, step: number) =>
  lerp(a, b, Math.min(1, step / Math.max(1e-15, distance(a, b))));
const nearest = (nodes: Point[], q: Point) => {
  let j = 0,
    d = Infinity;
  nodes.forEach((p, i) => {
    const n = distance(p, q);
    if (n < d) {
      d = n;
      j = i;
    }
  });
  return j;
};
export function* samplePlan(o: SamplingOptions): Generator<Frame> {
  const { env } = o,
    rng = random(o.seed);
  let checks = 0,
    first: number | null = null;
  const nodes: Point[] = [[...env.start]],
    parents = [-1],
    costs = [0],
    children: Set<number>[] = [new Set()];
  let bestPath: Point[] = [],
    best = Infinity;
  const other: Point[] = [[...env.goal]],
    otherParents = [-1];
  const goalEdges = new Map<number, number>();
  const valid = (a: Point, b: Point) => {
    checks++;
    return env.edge(a, b);
  };
  const sample = (biasTarget = env.goal) =>
    rng() < o.goalBias
      ? [...biasTarget]
      : env.bounds.map(([a, b]) => a + (b - a) * rng());
  const frame = (
    i: number,
    message: string,
    extra: Partial<Frame> = {},
  ): Frame => ({
    kind: "sampling",
    stats: {
      iterations: i,
      checks,
      expanded: nodes.length + (o.algorithm === "connect" ? other.length : 0),
      cost: best < Infinity ? best : null,
      firstSolution: first,
      status: best < Infinity ? "已找到路径 · 继续搜索" : "搜索中",
      message,
    },
    nodes,
    parents,
    costs,
    secondNodes: o.algorithm === "connect" ? other : undefined,
    secondParents: o.algorithm === "connect" ? otherParents : undefined,
    path: bestPath,
    ...extra,
  });
  if (env.clearance(env.start) <= 0 || env.clearance(env.goal) <= 0) {
    const f = frame(0, "起点或目标与障碍相交，请减小障碍尺寸。");
    f.stats.status = "起终点不可用";
    yield f;
    return;
  }
  if (distance(env.start, env.goal) < 1e-10) {
    bestPath = [[...env.start]];
    best = 0;
    first = 0;
    const f = frame(0, "起终点一致，无需扩展。");
    f.stats.status = "已完成";
    yield f;
    return;
  }
  for (let it = 1; it <= o.iterations; it++) {
    if (o.algorithm === "connect") {
      const swapped = it % 2 === 0,
        A = swapped ? other : nodes,
        AP = swapped ? otherParents : parents,
        B = swapped ? nodes : other,
        BP = swapped ? parents : otherParents;
      const target = sample(swapped ? env.start : env.goal),
        near = nearest(A, target),
        q = steer(A[near], target, o.step);
      let ok = valid(A[near], q);
      let touched = q;
      if (ok) {
        const ai = A.length;
        A.push(q);
        AP.push(near);
        let bi = nearest(B, q),
          reached = false;
        // The same target is held throughout Connect; every sub-edge is validated.
        const maxSteps =
          Math.ceil(
            env.bounds.reduce((s, [a, b]) => s + (b - a) ** 2, 0) ** 0.5 /
              o.step,
          ) + 2;
        for (let k = 0; k < maxSteps; k++) {
          if (distance(B[bi], q) < 1e-10) {
            reached = true;
            break;
          }
          const next = steer(B[bi], q, o.step);
          touched = next;
          if (!valid(B[bi], next)) break;
          B.push(next);
          BP.push(bi);
          bi = B.length - 1;
          if (distance(next, q) < 1e-10) {
            reached = true;
            break;
          }
        }
        if (reached) {
          const pa = trace(A, AP, ai),
            pb = trace(B, BP, bi);
          const full = swapped
            ? [...pb, ...pa.reverse().slice(1)]
            : [...pa, ...pb.reverse().slice(1)];
          bestPath = full;
          best = pathCost(full);
          first = it;
          const f = frame(
            it,
            "两棵树在同一配置会合；分别沿父节点回溯，拼接时只保留一次会合点。",
            { current: q, target, candidate: touched, accepted: true },
          );
          f.stats.status = "已找到路径";
          yield f;
          return;
        }
      }
      yield frame(
        it,
        ok
          ? "Extend成功；另一棵树朝固定目标逐段Connect，受阻后交换分工。"
          : "Extend受阻，当前轮不调用Connect；保留已有树。",
        { current: q, target, candidate: touched, accepted: ok },
      );
      continue;
    }
    const target = sample(),
      near = nearest(nodes, target),
      q = steer(nodes[near], target, o.step);
    if (distance(q, nodes[near]) < 1e-12) continue;
    if (!valid(nodes[near], q)) {
      yield frame(it, "候选连接受阻，拒绝这条边；不是只检查端点。", {
        candidate: q,
        target,
        accepted: false,
      });
      continue;
    }
    const ds = nodes.map((p) => distance(p, q)),
      nearby =
        o.algorithm === "star"
          ? ds
              .map((d, i) => ({ d, i }))
              .filter(
                (v) =>
                  v.d <=
                  Math.min(
                    o.radius,
                    12 *
                      (Math.log(nodes.length + 1) / (nodes.length + 1)) **
                        (1 / env.bounds.length),
                  ),
              )
              .map((v) => v.i)
          : [];
    let parent = near,
      g = costs[near] + ds[near];
    for (const j of nearby.sort(
      (a, b) => costs[a] + ds[a] - costs[b] - ds[b],
    )) {
      const c = costs[j] + ds[j];
      if (c < g - 1e-10 && valid(nodes[j], q)) {
        parent = j;
        g = c;
        break;
      }
    }
    const idx = nodes.length;
    nodes.push(q);
    parents.push(parent);
    costs.push(g);
    children.push(new Set());
    children[parent].add(idx);
    const rewired: number[] = [];
    const ancestor = (a: number, b: number) => {
      while (b >= 0) {
        if (a === b) return true;
        b = parents[b];
      }
      return false;
    };
    for (const j of nearby) {
      if (j === 0 || j === parent || ancestor(j, idx)) continue;
      const c = costs[idx] + ds[j];
      if (c >= costs[j] - 1e-10 || !valid(q, nodes[j])) continue;
      const delta = c - costs[j];
      children[parents[j]].delete(j);
      parents[j] = idx;
      children[idx].add(j);
      const stack = [j];
      while (stack.length) {
        const k = stack.pop()!;
        costs[k] += delta;
        stack.push(...children[k]);
      }
      rewired.push(j);
    }
    if (distance(q, env.goal) <= o.step && valid(q, env.goal))
      goalEdges.set(idx, distance(q, env.goal));
    for (const [j, last] of goalEdges) {
      const c = costs[j] + last;
      if (c < best - 1e-10) {
        best = c;
        bestPath = trace(nodes, parents, j);
        if (distance(bestPath.at(-1)!, env.goal) > 1e-10)
          bestPath.push([...env.goal]);
        if (first === null) first = it;
      }
    }
    yield frame(
      it,
      o.algorithm === "star"
        ? `新节点接入 #${parent}；本轮重连 ${rewired.length} 个邻居，后代成本随上游同步更新。`
        : "连接有效，新节点加入最近节点下面；记录父节点，满足条件时连接目标。",
      { candidate: q, target, accepted: true, rewired, current: q },
    );
  }
  const f = frame(
    o.iterations,
    best < Infinity
      ? "采样预算用完，保留目前最好的有效路径；有限预算不保证最短。"
      : "预算用完仍未找到路径。增加预算、调整步长或换一个种子再试。",
  );
  f.stats.status = best < Infinity ? "预算完成" : "预算内未找到路径";
  yield f;
}
