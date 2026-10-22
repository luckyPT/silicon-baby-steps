import { type Frame, type Point } from "./core.ts";
export interface Profile {
  duration: number;
  sample(t: number): { position: number; velocity: number };
}
export function trapezoid(
  distance: number,
  maxSpeed: number,
  acceleration: number,
): Profile {
  if (distance < 0 || maxSpeed <= 0 || acceleration <= 0)
    throw Error("Invalid profile parameters");
  const ta = Math.min(
      maxSpeed / acceleration,
      Math.sqrt(distance / acceleration),
    ),
    peak = acceleration * ta,
    flat =
      peak > 0 ? Math.max(0, (distance - acceleration * ta * ta) / peak) : 0,
    duration = 2 * ta + flat;
  return {
    duration,
    sample(t: number) {
      t = Math.max(0, Math.min(duration, t));
      if (t < ta)
        return {
          position: 0.5 * acceleration * t * t,
          velocity: acceleration * t,
        };
      if (t <= ta + flat)
        return {
          position: 0.5 * acceleration * ta * ta + peak * (t - ta),
          velocity: peak,
        };
      return {
        position: distance - 0.5 * acceleration * (duration - t) ** 2,
        velocity: acceleration * (duration - t),
      };
    },
  };
}
export function* trajectoryPlan(options: {
  mode: string;
  maxSpeed: number;
  acceleration: number;
  maxOmega: number;
  angularAcceleration: number;
}): Generator<Frame> {
  const { mode, maxSpeed, acceleration, maxOmega, angularAcceleration } =
      options,
    dt = 0.05;
  const linear = trapezoid(2, maxSpeed, acceleration),
    turn = trapezoid(Math.PI / 2, maxOmega, angularAcceleration);
  const first = mode === "limited" ? linear.duration : 2 / maxSpeed;
  const turning =
    mode === "instant"
      ? 0
      : mode === "limited"
        ? turn.duration
        : Math.PI / 2 / maxOmega;
  const duration = 2 * first + turning;
  const travelled: Point[] = [];
  for (let i = 0; i <= Math.ceil(duration / dt); i++) {
    const t = Math.min(duration, i * dt);
    let q: Point,
      v = 0,
      w = 0,
      phase = "直线前进";
    if (t < first) {
      const p =
        mode === "limited"
          ? linear.sample(t)
          : { position: Math.min(2, t * maxSpeed), velocity: maxSpeed };
      q = [2 + p.position, 2, 0];
      v = p.velocity;
    } else if (t < first + turning) {
      const p =
        mode === "limited"
          ? turn.sample(t - first)
          : {
              position: Math.min(Math.PI / 2, (t - first) * maxOmega),
              velocity: maxOmega,
            };
      q = [4, 2, p.position];
      w = p.velocity;
      phase = "拐点原地转向";
    } else {
      const p =
        mode === "limited"
          ? linear.sample(t - first - turning)
          : {
              position: Math.min(2, (t - first - turning) * maxSpeed),
              velocity: t < duration ? maxSpeed : 0,
            };
      q = [4, 2 + p.position, Math.PI / 2];
      v = p.velocity;
      phase = "转向后直线前进";
    }
    travelled.push(q);
    const done = t >= duration;
    yield {
      kind: "dwa",
      robot: q,
      current: q,
      path: [...travelled],
      route: [
        [2, 2],
        [4, 2],
        [4, 4],
      ],
      stats: {
        iterations: i,
        checks: 0,
        expanded: travelled.length,
        cost: Math.min(4, q[0] - 2 + q[1] - 2),
        firstSolution: done ? i : null,
        status: done
          ? "到达并停止"
          : mode === "limited"
            ? "满足本例速度与加速度限制"
            : "理想化方案 · 存在指令突变",
        message: `t=${t.toFixed(2)} s / ${duration.toFixed(2)} s；v=${v.toFixed(2)} m/s，ω=${((w * 180) / Math.PI).toFixed(1)}°/s。${phase}。${mode === "instant" ? "拐点朝向瞬间跳变，不能直接执行。" : mode === "stop" ? "直线与转向速度存在阶跃，未满足加速度限制。" : "当前是差速小车参考运动，不代表真实执行保证。"}`,
      },
    };
  }
}
