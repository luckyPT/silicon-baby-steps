"""Reproducible geometric single-tree RRT for the Episode 07 teaching model.

All internal configurations are radians. JSON presentation values are degrees.
The collision oracle uses link capsules against the cylinder's horizontal disc;
the full configuration-space raster is a display asset, never queried by RRT.
"""
from pathlib import Path
import json, math, time, platform
import numpy as np
from arm_model import clearance

B=Path(__file__).parent; A=B/'assets'; Q=B/'qa'
START=np.radians([-30.,90.]); GOAL=np.radians([-30.,150.])
LIMIT=np.radians(150.); STEP=np.radians(10.); CONNECT=np.radians(10.)
RESOLUTION=np.radians(.5); BIAS=.1; BUDGET=1500

def clearances(qs):
    qs=np.asarray(qs); t=qs[:,0]; u=qs[:,0]+qs[:,1]
    p=np.stack((np.cos(t),np.sin(t)),axis=1)
    e=p+np.stack((np.cos(u),np.sin(u)),axis=1)
    obstacle=np.array([.9,.5]); out=[]
    for a,b in [(np.zeros_like(p),p),(p,e)]:
        v=b-a; k=np.clip(np.sum((obstacle-a)*v,axis=1)/np.sum(v*v,axis=1),0,1)
        out.append(np.linalg.norm(a+k[:,None]*v-obstacle,axis=1)-.2)
    return np.minimum(*out)

class MotionValidator:
    def __init__(self): self.calls=0; self.configurations=0
    def check(self,a,b):
        self.calls+=1
        if np.any(np.abs(a)>LIMIT+1e-12) or np.any(np.abs(b)>LIMIT+1e-12):
            return False,{'reason':'joint_limit'}
        n=max(2,math.ceil(float(np.max(np.abs(b-a)))/RESOLUTION)+1)
        qs=np.linspace(a,b,n); self.configurations+=n
        cs=clearances(qs); k=int(np.argmin(cs))
        # Every material point moves at most 2|dq1|+|dq2| metres.
        # Subtract a full interval bound, conservatively certifying the gaps.
        bound=(2*abs(b[0]-a[0])+abs(b[1]-a[1]))/(n-1)
        low=float(cs[k]-bound)
        return low>0,{'sample_count':n,'sampled_min_clearance_m':float(cs[k]),
                      'continuous_clearance_lower_bound_m':low,
                      'critical_q_degrees':np.degrees(qs[k]).tolist(),
                      'endpoint_clearance_m':float(cs[-1]),
                      'reason':'certified_clear' if low>0 else ('collision' if cs[k]<=0 else 'insufficient_clearance_bound')}

def deg(q): return np.degrees(q).tolist()

def solve(seed):
    rng=np.random.default_rng(seed); val=MotionValidator()
    nodes=[START.copy()]; parents=[-1]; attempts=[]; found=False; goal_index=None
    assert clearances(np.array([START,GOAL])).min()>0
    begin=time.perf_counter()
    for iteration in range(BUDGET):
        biased=bool(rng.random()<BIAS)
        sample=GOAL.copy() if biased else rng.uniform(-LIMIT,LIMIT,2)
        near=int(np.argmin(np.linalg.norm(np.asarray(nodes)-sample,axis=1)))
        a=nodes[near]; d=float(np.linalg.norm(sample-a))
        if d<1e-12: continue
        new=a+min(1.,STEP/d)*(sample-a)
        valid,detail=val.check(a,new)
        event={'iteration':iteration+1,'sample':deg(sample),'from':deg(a),'to':deg(new),
               'parent':near,'tree_count_before':len(nodes),'valid':valid,
               'goal_biased':biased,'validation':detail,'added_index':None,'goal_connection':None}
        if valid:
            nodes.append(new.copy()); parents.append(near); idx=len(nodes)-1;event['added_index']=idx
            if float(np.linalg.norm(new-GOAL))<=CONNECT+1e-12:
                ok,goal_detail=val.check(new,GOAL)
                event['goal_connection']={'from':deg(new),'to':deg(GOAL),'valid':ok,'validation':goal_detail}
                if ok:
                    if np.linalg.norm(new-GOAL)<1e-10:goal_index=idx
                    else:nodes.append(GOAL.copy());parents.append(idx);goal_index=len(nodes)-1
                    found=True
        attempts.append(event)
        if found:break
    elapsed=time.perf_counter()-begin; indices=[]
    if found:
        k=goal_index
        while k>=0:indices.append(k);k=parents[k]
        indices.reverse()
    path=[deg(nodes[k]) for k in indices]
    length=sum(float(np.linalg.norm(nodes[b]-nodes[a])) for a,b in zip(indices,indices[1:]))
    return {'seed':seed,'found':found,'iteration_budget':BUDGET,'iterations':len(attempts),
            'accepted_nodes':len(nodes),'collision_validation_calls':val.calls,
            'configuration_checks':val.configurations,'runtime_seconds':elapsed,
            'path_length_radians':length,'path_length_degrees':math.degrees(length),
            'path_indices':indices,'path':path,'goal_index':goal_index,
            'nodes':[deg(n) for n in nodes],'parents':parents,'attempts':attempts,
            'step_degrees':math.degrees(STEP),'goal_bias':BIAS,'connect_radius_degrees':math.degrees(CONNECT),
            'collision_resolution_degrees':math.degrees(RESOLUTION),'internal_units':'radians',
            'metric':'Euclidean in the bounded two-angle configuration space; no wrap',
            'environment':{'python':platform.python_version(),'platform':platform.platform()},
            'timing_scope':'RRT loop including nearest-neighbour and collision checks; excludes map raster and rendering'}

def main():
    A.mkdir(exist_ok=True);Q.mkdir(exist_ok=True)
    runs=[solve(s) for s in [1,7,42]]
    for r in runs:
        print({k:r[k] for k in ['seed','found','iterations','accepted_nodes','collision_validation_calls','path_length_degrees','runtime_seconds']},flush=True)
    main=runs[0];assert main['found']
    (A/'rrt_run.json').write_text(json.dumps(main,ensure_ascii=False,indent=2))
    (A/'rrt_comparison.json').write_text(json.dumps(runs,ensure_ascii=False,indent=2))
    val=MotionValidator();valid,detail=val.check(np.radians([-30,90]),np.radians([-36,98]))
    assert valid
    direct_ok,direct=val.check(START,GOAL);assert not direct_ok and direct['endpoint_clearance_m']>0
    path_clear=[]
    for a,b in zip(main['path'],main['path'][1:]):
        # Independent, denser validation of the executed route.
        qs=np.linspace(a,b,501);cs=np.array([clearance(q) for q in qs])
        loss=(2*abs(b[0]-a[0])+abs(b[1]-a[1]))*math.pi/180/500
        path_clear.append(float(cs.min()-loss))
    assert min(path_clear)>0
    for r in runs:
        assert len(r['nodes'])==len(r['parents'])
        for i,p in enumerate(r['parents']):assert p<i
        for e in r['attempts']:
            if e['valid']:assert e['validation']['continuous_clearance_lower_bound_m']>0
    nearest_event=next(i for i,e in enumerate(main['attempts']) if e['tree_count_before']>=12 and e['parent']<e['tree_count_before']-3 and e['valid'])
    report={'status':'passed','example_extension':{'from':[-30,90],'sample':[-60,130],'to':[-36,98],**detail},
            'direct_edge':direct,'executed_path_min_certified_clearance_m':min(path_clear),
            'nearest_example_attempt_index':nearest_event,
            'runs':[{k:r[k] for k in ['seed','found','iterations','collision_validation_calls','path_length_degrees']} for r in runs],
            'geometry':'Same fixed-base planar 2R model as Episode 06; capsule radius .05m, obstacle (.9,.5), radius .15m',
            'limits':'This certifies the specified geometric model, not hardware or dynamics.'}
    (Q/'algorithm_validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
