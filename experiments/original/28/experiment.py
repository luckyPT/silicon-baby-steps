"""Recompute the four kinematic pushcart runs from episode 28."""
import json
from pathlib import Path

import numpy as np
from scipy.interpolate import CubicSpline
from scipy.optimize import minimize

DT, HORIZON, WHEELBASE = .1, 20, .19
BACK, FRONT, HALF_WIDTH = -.055, .235, .066
ROAD_HALF_WIDTH, ROAD_BUFFER = .235, .010
MAX_SPEED, REFERENCE_SPEED = .90, .66
MAX_ACC, MAX_STEER, MAX_STEER_RATE, MAX_LAT_ACC = .75, .62, 1.7, 1.03
GOAL, MAX_X = 1.78, 1.84
INITIAL = np.array([-1.6, 0., 0., .35, 0.])
CORNERS = [(dx, dy) for dx in (BACK, FRONT) for dy in (-HALF_WIDTH, HALF_WIDTH)]
ROAD_X = [-2, -1.6, -1.05, -.45, .2, .8, 1.35, 1.8, 2.3]
ROAD_Y = [0, 0, 0, .30, -.26, .21, 0, 0, 0]
road = CubicSpline(ROAD_X, ROAD_Y, bc_type="natural")

def advance(state, command, dt=DT):
    x, y, heading, speed, steer = state
    acc, steer_rate = command
    return np.array([
        x + dt * speed * np.cos(heading),
        y + dt * speed * np.sin(heading),
        heading + dt * speed * np.tan(steer) / WHEELBASE,
        speed + dt * acc,
        steer + dt * steer_rate,
    ])

def road_margin(states):
    x, y, heading = states[:, :3].T
    c, s = np.cos(heading), np.sin(heading)
    gaps = [
        ROAD_HALF_WIDTH - abs(y + dx * s + dy * c - road(x + dx * c - dy * s))
        for dx, dy in CORNERS
    ]
    return np.min(gaps, axis=0)

class Prediction:
    def __init__(self, initial):
        self.initial = initial
        self.last = None

    def compute(self, controls):
        if np.array_equal(self.last, controls):
            return
        self.last = controls.copy()
        state = self.initial
        sensitivity = np.zeros((5, HORIZON * 2))
        states, derivatives = [], []
        u = controls.reshape(HORIZON, 2)
        for i, command in enumerate(u):
            _, _, heading, speed, steer = state
            c, s, tan = np.cos(heading), np.sin(heading), np.tan(steer)
            jac = np.eye(5)
            jac[0, 2:4] = [-DT * speed * s, DT * c]
            jac[1, 2:4] = [DT * speed * c, DT * s]
            jac[2, 3:5] = [DT * tan / WHEELBASE, DT * speed * (1 + tan**2) / WHEELBASE]
            sensitivity = jac @ sensitivity
            sensitivity[3, 2*i] += DT
            sensitivity[4, 2*i+1] += DT
            state = advance(state, command)
            states.append(state)
            derivatives.append(sensitivity)
        self.states = np.asarray(states)
        x, y, angle, v, steer = self.states.T
        gx, gy, ga, gv, gs = np.asarray(derivatives).transpose(1, 0, 2)
        slope = road(x, 1)
        ey = y - road(x)
        ey_jac = gy - slope[:, None] * gx
        ea = angle - np.arctan(slope)
        ea_jac = ga - (road(x, 2) / (1 + slope**2))[:, None] * gx
        vmax_to_stop = np.sqrt(2 * MAX_ACC * np.maximum(GOAL - x, 0))
        ref_speed = np.minimum(REFERENCE_SPEED, vmax_to_stop)
        slope_speed = np.where(
            (vmax_to_stop < REFERENCE_SPEED) & (vmax_to_stop > 1e-8),
            -MAX_ACC / np.maximum(vmax_to_stop, 1e-8), 0,
        )
        ev = v - ref_speed
        ev_jac = gv - slope_speed[:, None] * gx
        self.cost = float(np.sum(
            105*ey**2 + 3*ea**2 + 10*ev**2 + .07*u[:, 0]**2 + .028*u[:, 1]**2
        ) + 7*ey[-1]**2 + 1.2*(x[-1]-GOAL)**2 + 3*v[-1]**2)
        self.gradient = (
            (210*ey[:, None]*ey_jac + 6*ea[:, None]*ea_jac + 20*ev[:, None]*ev_jac).sum(0)
            + np.tile([.14, .056], HORIZON)*controls
            + 14*ey[-1]*ey_jac[-1] + 2.4*(x[-1]-GOAL)*gx[-1] + 6*v[-1]*gv[-1]
        )
        c, s = np.cos(angle), np.sin(angle)
        values, rows = [], []
        for dx, dy in CORNERS:
            cx, cy = x + dx*c - dy*s, y + dx*s + dy*c
            g_cx = gx + (-dx*s-dy*c)[:, None]*ga
            g_cy = gy + (dx*c-dy*s)[:, None]*ga
            e = cy - road(cx)
            de = g_cy - road(cx, 1)[:, None]*g_cx
            values.extend([ROAD_HALF_WIDTH-ROAD_BUFFER-e, ROAD_HALF_WIDTH-ROAD_BUFFER+e])
            rows.extend([-de, de])
        tan = np.tan(steer)
        lateral = v**2 * tan / WHEELBASE
        dl = (2*v*tan/WHEELBASE)[:, None]*gv + (v**2*(1+tan**2)/WHEELBASE)[:, None]*gs
        values.extend([v, MAX_SPEED-v, MAX_STEER-steer, MAX_STEER+steer, MAX_LAT_ACC-lateral, MAX_LAT_ACC+lateral, MAX_X-x])
        rows.extend([gv, -gv, -gs, gs, -dl, dl, -gx])
        self.constraints = np.concatenate(values)
        self.constraint_jac = np.concatenate(rows)

    def evaluate(self, controls, name):
        self.compute(controls)
        return getattr(self, name)

def feedback(state, warm):
    prediction = Prediction(state)
    def evaluate(name):
        return lambda z: prediction.evaluate(z, name)
    result = minimize(evaluate("cost"), warm.ravel(), jac=evaluate("gradient"), method="SLSQP",
                      bounds=[(-MAX_ACC, MAX_ACC), (-MAX_STEER_RATE, MAX_STEER_RATE)]*HORIZON,
                      constraints={"type": "ineq", "fun": evaluate("constraints"), "jac": evaluate("constraint_jac")},
                      options={"maxiter": 125, "ftol": 2e-5})
    prediction.compute(result.x)
    if not result.success or prediction.constraints.min() < -1e-4:
        raise RuntimeError(f"No verified feasible MPC solution: {result.message}, {prediction.constraints.min():.5g}")
    return result.x.reshape(HORIZON, 2), prediction.states.copy(), int(result.nit)

def baseline(state, preview):
    x, y, angle, speed, steer = state
    ahead = .33 if preview else .035
    error = np.arctan2(road(x+ahead)-y, ahead) - angle
    aim = np.clip(np.arctan2(2*WHEELBASE*np.sin(error), ahead), -MAX_STEER, MAX_STEER)
    acceleration = np.clip((.85-speed)*3, -MAX_ACC, MAX_ACC)
    steering = np.clip((aim-steer)*7, -MAX_STEER_RATE, MAX_STEER_RATE)
    return np.array([acceleration, steering])

def simulate(mode):
    state = INITIAL.copy()
    history, fine, predictions, iterations = [state.tolist()], [state.tolist()], [], []
    warm = np.zeros((HORIZON, 2))
    optimized = mode in {"mpc", "disturbance"}
    perturbation_time = None
    for i in range(360):
        if optimized:
            commands, forecast, count = feedback(state, warm)
            action = commands[0]
            warm = np.vstack([commands[1:], commands[-1:]])
            predictions.append(forecast[:, :2].tolist())
            iterations.append(count)
        else:
            action = baseline(state, mode == "preview")
        substeps = [advance(state, action, DT*k/10) for k in range(1, 11)]
        fine.extend(substeps)
        state = substeps[-1].copy()
        if mode == "disturbance" and i == 25:
            state[1] += .025
            state[2] += .045
            perturbation_time = round((i+1)*DT, 3)
            fine.append(state.copy())
        history.append(state.tolist())
        if not optimized and road_margin(state[None, :])[0] < -.035:
            break
        if (state[0] > 1.735 and state[3] < .08) or state[0] > MAX_X:
            break
    track = np.asarray(history)
    check = np.asarray(fine)
    margins = road_margin(check)
    result = {
        "states": history,
        "predictions": predictions,
        "perturbationTime": perturbation_time,
        "metrics": {
            "duration": round((len(history)-1)*DT, 3),
            "minMargin": float(margins.min()),
            "endSpeed": float(state[3]),
            "maxDeviation": float(np.max(np.abs(track[:, 1] - road(track[:, 0])))),
            "maxLateralAcceleration": float(np.max(np.abs(check[:, 3]**2*np.tan(check[:, 4])/WHEELBASE))),
            "successfulSolves": len(iterations),
        },
    }
    if optimized:
        assert margins.min() > 0 and state[0] > 1.735 and 0 <= state[3] < .08
        assert result["metrics"]["maxLateralAcceleration"] < 1.05
    else:
        assert margins.min() < 0
    return result

def make_replay():
    road_x = np.linspace(-1.92, 2.08, 161)
    views = []
    labels = {"reactive": "短视跟线", "preview": "固定高速预瞄", "mpc": "MPC 正常工况", "disturbance": "MPC 受扰重规划"}
    for key, label in labels.items():
        views.append({"id": key, "label": label, **simulate(key)})
    return {
        "episode": 28,
        "mode": "recorded-experiment",
        "scope": "回放与本集主对照相同的自行车运动学模型。轨迹由 Python 离线计算，播放器按采样时刻展示。",
        "dt": DT,
        "road": [[float(x), float(road(x))] for x in road_x],
        "roadHalfWidth": ROAD_HALF_WIDTH,
        "footprint": [BACK, FRONT, HALF_WIDTH],
        "views": views,
    }

if __name__ == "__main__":
    import argparse

    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--output", type=Path)
    args = cli.parse_args()
    data = make_replay()
    for view in data["views"]:
        print(view["label"], json.dumps(view["metrics"], ensure_ascii=False))
    if args.output:
        args.output.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n")
