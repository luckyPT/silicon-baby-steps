/** Episode 16: deterministic branches of the preserved Python teaching experiment.
 * Static 2D point robot; obstacle radii already include robot inflation.
 * These virtual forces are geometric directions, not motor force commands.
 */
export type PFPoint = [number, number];
export type PFMode = 'baseline' | 'subgoal';
export const PF_MODEL = {
  obstacles: [[2, .6], [2, -.6]] as PFPoint[],
  radius: .4,
  start: [.4, .03] as PFPoint,
  goal: [5, 0] as PFPoint,
  low: [-.5, -2.6] as PFPoint,
  high: [5.6, 2.6] as PFPoint,
  subgoals: [[.8, -2.2], [3.6, -2.2], [5, 0]] as PFPoint[],
};
export const PF_DEFAULTS = { attraction: 1, repulsion: 2.1444572361897034, influence: 1.5, gain: .035, maxStep: .075, budget: 2400 };
export type PFOptions = typeof PF_DEFAULTS;
export type PFStatus = 'reached' | 'stagnated' | 'subgoal_stagnated' | 'iteration_budget_exhausted';
export interface PFResult {
  mode: PFMode; options: PFOptions; status: PFStatus; iterations: number;
  path: PFPoint[]; goals: PFPoint[]; events: { step: number; kind: 'stagnation' | 'temporary_goals_enabled' }[];
  lengthM: number; minVertexClearanceM: number; goalDistanceM: number;
  allEdgesCollisionFree: boolean; planningChecks: number; validationChecks: number;
}
const norm = (p: PFPoint) => Math.hypot(p[0], p[1]);
const subtract = (a: PFPoint, b: PFPoint): PFPoint => [a[0] - b[0], a[1] - b[1]];
export const pfDistance = (a: PFPoint, b: PFPoint) => norm(subtract(a, b));
export const pfClearance = (p: PFPoint) => Math.min(...PF_MODEL.obstacles.map(c => pfDistance(c, p) - PF_MODEL.radius));
export function pfEdge(a: PFPoint, b: PFPoint): boolean {
  if (![...a, ...b].every(Number.isFinite)) return false;
  if ([a, b].some(p => p.some((v, i) => v < PF_MODEL.low[i] || v > PF_MODEL.high[i]))) return false;
  const d = subtract(b, a), dd = Math.max(d[0] * d[0] + d[1] * d[1], 1e-18);
  return PF_MODEL.obstacles.every(c => {
    const t = Math.max(0, Math.min(1, ((c[0] - a[0]) * d[0] + (c[1] - a[1]) * d[1]) / dd));
    return pfDistance(c, [a[0] + t * d[0], a[1] + t * d[1]]) - PF_MODEL.radius > 1e-5;
  });
}
export function pfPotential(p: PFPoint, goal = PF_MODEL.goal, options = PF_DEFAULTS): number {
  if (pfClearance(p) <= 0) return Infinity;
  return .5 * options.attraction * pfDistance(p, goal) ** 2 + PF_MODEL.obstacles.reduce((u, c) => {
    const rho = pfDistance(p, c) - PF_MODEL.radius;
    return u + .5 * options.repulsion * Math.max(1 / rho - 1 / options.influence, 0) ** 2;
  }, 0);
}
export function pfForces(p: PFPoint, goal = PF_MODEL.goal, options = PF_DEFAULTS) {
  if (pfClearance(p) <= 0) throw Error('势场只在障碍外定义');
  const attraction: PFPoint = [(goal[0] - p[0]) * options.attraction, (goal[1] - p[1]) * options.attraction];
  const repulsion: PFPoint = [0, 0];
  for (const c of PF_MODEL.obstacles) {
    const v = subtract(p, c), r = norm(v), rho = r - PF_MODEL.radius;
    if (rho < options.influence) {
      const strength = options.repulsion * (1 / rho - 1 / options.influence) / rho ** 2;
      repulsion[0] += strength * v[0] / r;
      repulsion[1] += strength * v[1] / r;
    }
  }
  const total: PFPoint = [attraction[0] + repulsion[0], attraction[1] + repulsion[1]];
  return { attraction, repulsion, total };
}
export function runPotentialField(mode: PFMode, partial: Partial<PFOptions> = {}): PFResult {
  const options = { ...PF_DEFAULTS, ...partial };
  if (!Object.values(options).every(v => Number.isFinite(v) && v > 0) || !Number.isInteger(options.budget) || options.budget > 2400)
    throw Error('参数必须是有限正数，迭代预算为1—2400的整数');
  let p: PFPoint = [...PF_MODEL.start], temporary = false, subindex = 0, planningChecks = 0, iterations = 0;
  let status: PFStatus = 'iteration_budget_exhausted';
  const path: PFPoint[] = [[...p]], goals: PFPoint[] = [[...PF_MODEL.goal]], events: PFResult['events'] = [];
  for (let k = 0; k < options.budget; k++) {
    iterations = k + 1;
    if (pfDistance(p, PF_MODEL.goal) < .07) { status = 'reached'; break; }
    let g = PF_MODEL.goal;
    if (mode === 'subgoal' && temporary) {
      g = PF_MODEL.subgoals[subindex];
      if (pfDistance(p, g) < .14) {
        subindex++;
        if (subindex >= PF_MODEL.subgoals.length) { g = PF_MODEL.goal; temporary = false; }
        else g = PF_MODEL.subgoals[subindex];
      }
    }
    const force = pfForces(p, g, options).total;
    let step: PFPoint = [options.gain * force[0], options.gain * force[1]];
    const stepLength = norm(step);
    if (stepLength > options.maxStep) step = [step[0] * options.maxStep / stepLength, step[1] * options.maxStep / stepLength];
    for (let back = 0; back < 12; back++) {
      const candidate: PFPoint = [p[0] + step[0], p[1] + step[1]];
      planningChecks++;
      if (pfEdge(p, candidate) && pfPotential(candidate, g, options) <= pfPotential(p, g, options) + 1e-10) {
        p = candidate; break;
      }
      step = [step[0] * .5, step[1] * .5];
    }
    path.push([...p]); goals.push([...g]);
    const stuck = k > 70 && Math.max(...path.slice(-60).map(q => pfDistance(q, p))) < .003;
    if (stuck) {
      events.push({ step: k, kind: 'stagnation' });
      if (mode === 'baseline') { status = 'stagnated'; break; }
      if (temporary) { status = 'subgoal_stagnated'; break; }
      temporary = true; subindex = 0;
      events.push({ step: k, kind: 'temporary_goals_enabled' });
    }
  }
  let lengthM = 0, allEdgesCollisionFree = true;
  for (let i = 1; i < path.length; i++) {
    lengthM += pfDistance(path[i - 1], path[i]);
    allEdgesCollisionFree = pfEdge(path[i - 1], path[i]) && allEdgesCollisionFree;
  }
  return { mode, options, status, iterations, path, goals, events, lengthM,
    minVertexClearanceM: Math.min(...path.map(pfClearance)), goalDistanceM: pfDistance(p, PF_MODEL.goal),
    allEdgesCollisionFree, planningChecks, validationChecks: path.length - 1 };
}
