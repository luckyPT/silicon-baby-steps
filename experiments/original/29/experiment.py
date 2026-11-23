"""Recompute the episode 29 finite-horizon dead-end experiment."""
import argparse
import json
from pathlib import Path

import numpy as np
from scipy.optimize import minimize

DT, STEPS, BATCH = .22, 32, 3600
START, GOAL = np.array([.91, 0., 0.]), np.array([1.85, 0.])
LIMIT = np.array([.98, 2.75])
WALLS = np.array([[.30, .45, 1.46, .58], [-.43, -.58, 1.46, -.45], [1.33, -.45, 1.46, .45]])
CENTER = (WALLS[:, 2:] + WALLS[:, :2]) / 2
HALF = (WALLS[:, 2:] - WALLS[:, :2]) / 2
RADIUS, MARGIN, SUCCESS_RADIUS = .14, .028, .14
SUBSTEPS = [.25, .5, .75, 1.]

def advance(state, control, dt=DT):
    v, w = np.moveaxis(control, -1, 0)
    direction = state[..., 2] + w*dt/2
    distance = v*dt*np.sinc(w*dt/(2*np.pi))
    return state + np.stack((distance*np.cos(direction), distance*np.sin(direction), w*dt), axis=-1)

def rollout(state, controls):
    state = np.broadcast_to(state, (*controls.shape[:-2], 3))
    states = [state]
    for control in np.moveaxis(controls, -2, 0):
        state = advance(state, control)
        states.append(state)
    return np.stack(states, axis=-2)

def clearance(points):
    outside = np.abs(points[..., None, :2] - CENTER) - HALF
    norms = np.linalg.norm(np.maximum(outside, 0), axis=-1)
    return (norms + np.minimum(outside.max(axis=-1), 0)).min(axis=-1) - RADIUS

def distances(states, controls):
    mid = advance(states[..., :-1, :], controls, DT/2)
    return np.concatenate((clearance(states[..., 1:, :]), clearance(mid)), axis=-1)

def score(states, controls):
    d = ((states[..., 1:, :2] - GOAL)**2).sum(axis=-1)
    effort = ((controls / LIMIT)**2).sum(axis=(-1, -2))
    changes = ((np.diff(controls, axis=-2) / LIMIT)**2).sum(axis=(-1, -2))
    return 65*d[..., -1] + .06*d.sum(axis=-1) + .021*effort + .10*changes

def initial_plan(reverse):
    u = np.zeros((STEPS, 2))
    if reverse:
        u[:5, 0] = -.92
        u[5:9, 1] = 1.78
        u[9:14, 0] = .93
        u[14:18, 1] = -1.78
        u[18:27, 0] = .98
        u[27:29, 1] = -2.75
        u[29:, 0] = .72
    else:
        u[0, 0] = .92
    return u

def solve_slsqp(state, initial):
    last, data = None, None
    best, best_cost = initial, np.inf

    def evaluate(flat):
        nonlocal last, data, best, best_cost
        if last is not None and np.array_equal(last, flat):
            return data
        u = flat.reshape(STEPS, 2)
        pos = rollout(state, u)
        heading = pos[:-1, 2]
        v, w = u.T
        jac = np.zeros((STEPS+1, 3, 2*STEPS))

        def step_derivatives(dt):
            arg = w*dt/2
            angle = heading + arg
            sinc = np.sinc(arg/np.pi)
            dsinc = np.divide(arg*np.cos(arg)-np.sin(arg), arg*arg,
                              out=np.zeros_like(arg), where=np.abs(arg)>1e-6)
            direction = np.stack((np.cos(angle), np.sin(angle)), axis=1)
            turn = np.stack((-np.sin(angle), np.cos(angle)), axis=1)
            input_jac = np.empty((STEPS, 2, 2))
            input_jac[:, :, 0] = dt*sinc[:, None]*direction
            input_jac[:, :, 1] = (v*dt*dt/2)[:, None]*(dsinc[:, None]*direction+sinc[:, None]*turn)
            return input_jac, (dt*v*sinc)[:, None]*turn

        direct, yaw = step_derivatives(DT)
        for i in range(STEPS):
            jac[i+1] = jac[i]
            jac[i+1, :2] += yaw[i, :, None]*jac[i, 2, :]
            jac[i+1, :2, 2*i:2*i+2] = direct[i]
            jac[i+1, 2, 2*i+1] = DT
        sampled, derivatives = [pos[1:, :2]], [jac[1:, :2]]
        for fraction in SUBSTEPS[:-1]:
            direct, yaw = step_derivatives(DT*fraction)
            partial = jac[:-1, :2].copy() + yaw[:, :, None]*jac[:-1, 2:3, :]
            for i in range(STEPS):
                partial[i, :, 2*i:2*i+2] = direct[i]
            sampled.append(advance(pos[:-1], u, DT*fraction)[:, :2])
            derivatives.append(partial)
        directions = np.concatenate(sampled)[:, None] - CENTER
        outside = np.abs(directions) - HALF
        positive = np.maximum(outside, 0)
        norm = np.linalg.norm(positive, axis=-1)
        signed = norm + np.minimum(outside.max(axis=-1), 0)
        row, wall = np.arange(len(signed)), signed.argmin(axis=1)
        normals = np.divide(positive, norm[..., None], out=np.zeros_like(positive), where=norm[..., None]>0)
        inside_rows, inside_walls = np.where(norm == 0)
        normals[inside_rows, inside_walls, outside[inside_rows, inside_walls].argmax(axis=1)] = 1
        normals *= np.where(directions >= 0, 1, -1)
        gap = signed[row, wall] - RADIUS - MARGIN
        gap_jac = np.einsum('ki,kij->kj', normals[row, wall], np.concatenate(derivatives))
        error = pos[1:, :2] - GOAL
        error[:-1] *= .06
        error[-1] *= 65.06
        grad = 2*np.einsum('ki,kij->j', error, jac[1:, :2])
        diff = np.diff(u, axis=0) / LIMIT**2
        grad_u = .042*u/LIMIT**2
        grad_u[:-1] -= .20*diff
        grad_u[1:] += .20*diff
        value = score(pos, u)
        if gap.min() > -1e-7 and value < best_cost:
            best, best_cost = u.copy(), value
        last = flat.copy()
        data = value, grad+grad_u.ravel(), gap, gap_jac
        return data

    minimize(lambda a: evaluate(a)[0], initial.ravel(), jac=lambda a: evaluate(a)[1],
             method='SLSQP', bounds=[(-v, v) for v in np.tile(LIMIT, STEPS)],
             constraints={'type':'ineq', 'fun':lambda a:evaluate(a)[2], 'jac':lambda a:evaluate(a)[3]},
             options={'maxiter':20, 'ftol':3e-5})
    return best

def sample_maneuvers(rng, count):
    result = np.zeros((count, STEPS, 2))
    indices = np.arange(STEPS)[None, :]
    cuts = np.cumsum(np.column_stack([rng.integers(lo, hi+1, count) for lo, hi in
        [(4,7), (3,5), (3,6), (3,5), (6,10), (2,5), (2,5)]]), axis=1)
    sign = np.where(rng.random(count) > .30, 1., -1.)
    values = [(-rng.uniform(.64,.98,count),rng.uniform(-.12,.12,count)),
        (rng.uniform(-.08,.25,count),sign*rng.uniform(1.7,2.75,count)),
        (rng.uniform(.7,.98,count),rng.uniform(-.14,.14,count)),
        (rng.uniform(.05,.25,count),-sign*rng.uniform(1.7,2.75,count)),
        (rng.uniform(.78,.98,count),rng.uniform(-.14,.14,count)),
        (rng.uniform(.07,.26,count),-sign*rng.uniform(1.55,2.75,count)),
        (rng.uniform(.60,.90,count),rng.uniform(-.14,.14,count))]
    left = np.zeros((count, 1))
    for i, (v, w) in enumerate(values):
        right = cuts[:, i, None]
        result += ((indices >= left) & (indices < right))[:, :, None]*np.stack((v, w), axis=1)[:, None, :]
        left = right
    return result

def solve_sampling(state, nominal, rng, first, structured):
    preview = []
    times = np.linspace(0, 6, STEPS)
    left = np.minimum(times.astype(int), 5)
    fraction = (times-left)[None, :, None]
    for iteration in range(4 if first else 2):
        knots = rng.normal(size=(BATCH, 7, 2))
        noise = (1-fraction)*knots[:, left, :]+fraction*knots[:, left+1, :]
        scale = np.array([.95, 2.14] if first and iteration<3 else [.45, 1.02])
        candidates = np.clip(nominal + noise*scale, -LIMIT, LIMIT)
        if structured and first and iteration == 0:
            candidates[-BATCH//2:] = sample_maneuvers(rng, BATCH//2)
        candidates[0] = nominal
        paths = rollout(state, candidates)
        margins = distances(paths, candidates)
        feasible = margins.min(axis=-1) >= MARGIN
        costs = score(paths, candidates)
        effective = costs + 2200*np.maximum(MARGIN-margins, 0).sum(axis=-1)
        weights = np.exp(-(effective-effective.min())/.43)
        weights /= weights.sum()
        updated = (weights[:, None, None]*candidates).sum(axis=0)
        updated_path = rollout(state, updated)
        unsafe = distances(updated_path, updated).min() < MARGIN
        deteriorated = feasible[0] and score(updated_path, updated) > costs[0]+.015
        if unsafe or deteriorated:
            safe = np.flatnonzero(feasible)
            updated = candidates[safe[np.argmin(costs[safe])]] if len(safe) else np.zeros_like(nominal)
        if first and iteration == 0:
            selected = np.unique(np.r_[np.linspace(0, BATCH-1, 20, dtype=int), np.argsort(effective)[:4]])
            preview = paths[selected, :, :2].round(5).tolist()
        nominal = updated
    return nominal, preview

LABELS = {
    'cold': 'SLSQP · 直行初值', 'warm': 'SLSQP · 倒车初值',
    'mppi': 'MPPI · 首批加入倒车组合', 'plain': 'MPPI · 仅随机扰动',
}

def run(kind, seed=29):
    rng = np.random.default_rng(seed)
    state = START.copy()
    nominal = initial_plan(kind == 'warm')
    states, controls, forecasts, minimums, proposals = [state], [], [], [], []
    for step in range(45):
        if kind in ('mppi', 'plain'):
            u, samples = solve_sampling(state, nominal, rng, first=step == 0, structured=kind == 'mppi')
            if step == 0:
                proposals = samples
        else:
            u = solve_slsqp(state, nominal)
        forecasts.append(rollout(state, u)[:, :2])
        act = u[0].copy()
        segment = advance(state, act, DT*np.arange(1, 13)/12)
        gap = float(clearance(segment).min())
        if gap < MARGIN-.004:
            act = np.zeros(2)
            segment = state[None, :]
            gap = float(clearance(segment).min())
        state = segment[-1]
        states.append(state)
        controls.append(act)
        minimums.append(gap)
        nominal = np.vstack((u[1:], np.zeros((1, 2))))
        if np.linalg.norm(state[:2]-GOAL) < SUCCESS_RADIUS:
            break
        if step >= 14 and kind == 'cold' and np.max(np.abs(controls[-8:])) < .009:
            break
    end = float(np.linalg.norm(state[:2]-GOAL))
    return {
        'id': kind, 'label': LABELS[kind], 'seed': seed,
        'states': np.array(states).round(6).tolist(), 'controls': np.array(controls).round(6).tolist(),
        'predictions': np.array(forecasts).round(5).tolist(), 'samples': proposals,
        'metrics': {'success': end < SUCCESS_RADIUS, 'duration': round(len(controls)*DT, 2),
                    'clearance': round(min(minimums), 5), 'endDistance': round(end, 5)},
    }

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('public/experiments/29.json'))
    args = parser.parse_args()
    groups = [('cold', [29]), ('warm', [29]), ('mppi', range(29, 34)), ('plain', range(29, 32))]
    views, results = [], []
    for kind, seeds in groups:
        runs = [run(kind, seed) for seed in seeds]
        views.append(runs[0])
        results.append({'id': kind, 'label': LABELS[kind], 'runs': [
            {'seed': r['seed'], **r['metrics']} for r in runs]})
        print(kind, sum(r['metrics']['success'] for r in runs), '/', len(runs), runs[0]['metrics'], flush=True)
    data = {'episode': 29, 'mode': 'recorded-experiment', 'dt': DT, 'horizonSteps': STEPS,
            'batchSize': BATCH, 'radius': RADIUS, 'goalRadius': SUCCESS_RADIUS,
            'start': START.tolist(), 'goal': GOAL.tolist(), 'walls': WALLS.tolist(),
            'views': views, 'results': results}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(data, ensure_ascii=False, separators=(',', ':'))+'\n')

if __name__ == '__main__':
    main()
