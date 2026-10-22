"""Episode 08: Extend/Connect bidirectional geometric RRT, exact event log.

Radians internally. The shared oracle certifies whole edges in the specified
static 2R capsule/disc model. Display raster is never used by the planner.
"""
from pathlib import Path
import json, math, time
import numpy as np
from rrt import START, GOAL, LIMIT, STEP, MotionValidator, clearances, deg
from arm_model import clearance

B=Path(__file__).parent; A=B/'assets'; Q=B/'qa'

class BudgetExceeded(Exception): pass

class Oracle(MotionValidator):
    def __init__(self,budget):super().__init__();self.budget=budget
    def check(self,a,b):
        if self.calls>=self.budget:raise BudgetExceeded()
        return super().check(a,b)

def solve(seed,kind='connect',budget=1500,bias=0.):
    rng=np.random.default_rng(seed);v=Oracle(budget)
    trees={k:{'nodes':[q.copy()],'parents':[-1]} for k,q in [('S',START),('G',GOAL)]}
    events=[]; rounds=[]; active='S';found=False;meet={};outer=0
    begin=time.perf_counter()
    def extend(k,target,phase):
        tr=trees[k];nodes=tr['nodes'];near=int(np.argmin(np.linalg.norm(np.array(nodes)-target,axis=1)))
        old=nodes[near];dist=float(np.linalg.norm(target-old))
        if dist<1e-10:return 'Reached',near
        new=old+min(1.,STEP/dist)*(target-old)
        valid,detail=v.check(old,new)
        status=('Reached' if dist<=STEP+1e-12 else 'Advanced') if valid else 'Trapped'
        idx=None
        if valid: nodes.append(new.copy());tr['parents'].append(near);idx=len(nodes)-1
        events.append({'round':outer,'tree':k,'phase':phase,'target':deg(target),'from':deg(old),'to':deg(new),'parent':near,'added_index':idx,'valid':valid,'status':status,'validation':detail})
        return status,idx
    try:
        while v.calls<budget:
            outer+=1;before=len(events)
            # RRT comparator uses the same uniform sampler (bias=0); previous
            # episode's p=.1 baseline is reported separately, never conflated.
            sample=GOAL.copy() if bias and rng.random()<bias else rng.uniform(-LIMIT,LIMIT,2)
            status,idx=extend(active,sample,'Extend')
            if status!='Trapped':
                other='G' if active=='S' else 'S';target=trees[active]['nodes'][idx]
                if kind=='connect':
                    while True:
                        s,j=extend(other,target,'Connect')
                        if s!='Advanced':break
                    if s=='Reached':found=True;meet={active:idx,other:j}
                elif np.linalg.norm(target-GOAL)<=STEP+1e-12:
                    s,j=extend('S',GOAL,'Goal')
                    if s=='Reached':found=True;meet={'S':j}
            rounds.append({'round':outer,'active':active,'sample':deg(sample),'event_start':before,'event_end':len(events),'found':found})
            if found:break
            if kind=='connect':active='G' if active=='S' else 'S'
    except BudgetExceeded:pass
    elapsed=time.perf_counter()-begin
    def trace(k,i):
        out=[];tr=trees[k]
        while i>=0:out.append(i);i=tr['parents'][i]
        return out
    indices={};path=[]
    if found:
        indices['S']=trace('S',meet['S'])[::-1]
        path=[deg(trees['S']['nodes'][i]) for i in indices['S']]
        if kind=='connect':
            indices['G']=trace('G',meet['G'])
            path.extend(deg(trees['G']['nodes'][i]) for i in indices['G'][1:])
    return {'seed':seed,'algorithm':kind,'found':found,'validation_budget':budget,'motion_checks':v.calls,'configuration_checks':v.configurations,'outer_rounds':outer,'events':events,'rounds':rounds,'trees':{k:{'nodes':[deg(n) for n in t['nodes']],'parents':t['parents']} for k,t in trees.items()},'meeting_indices':meet,'path_indices':indices,'path':path,'path_length_degrees':sum(math.dist(a,b) for a,b in zip(path,path[1:])),'runtime_seconds':elapsed,'step_degrees':10,'goal_bias':bias,'sampling':'uniform bounded joint angles','internal_units':'radians'}

def main():
    A.mkdir(exist_ok=True);Q.mkdir(exist_ok=True)
    runs=[]
    for seed in range(1,31):
        for kind in ['single','connect']:runs.append(solve(seed,kind))
    for kind in ['single','connect']:
        rr=[r for r in runs if r['algorithm']==kind];ok=[r for r in rr if r['found']]
        print(kind,'success',len(ok),'/30','median checks',np.median([r['motion_checks'] for r in rr]),'median length',np.median([r['path_length_degrees'] for r in ok]),flush=True)
    main=next(r for r in runs if r['algorithm']=='connect' and r['seed']==1)
    assert main['found']
    lower=[]
    for r in runs:
        if not r['found']:continue
        assert np.allclose(r['path'][0],deg(START)) and np.allclose(r['path'][-1],deg(GOAL))
        for a,b in zip(r['path'],r['path'][1:]):
            qs=np.linspace(a,b,1001);cs=np.array([clearance(q) for q in qs])
            bound=math.pi/180*(2*abs(b[0]-a[0])+abs(b[1]-a[1]))/1000
            assert cs.min()-bound>0
            if r is main:lower.append(float(cs.min()-bound))
        for tr in r['trees'].values():
            for i,p in enumerate(tr['parents']):assert p<i
        for e in r['events']:
            assert (e['status']=='Trapped')==(not e['valid'])
            if e['valid']:assert e['validation']['continuous_clearance_lower_bound_m']>0
    # A simple exact arithmetic demo, separately verified rather than passed
    # off as the main stochastic run. Final remaining distance is under epsilon.
    demo_from=[-90.,-90.];demo_target=[-72.,-66.];demo=[];v=MotionValidator();q=np.array(demo_from)
    while np.linalg.norm(q-demo_target)>1e-9:
        delta=np.array(demo_target)-q;d=float(np.linalg.norm(delta));new=q+min(1,10/d)*delta
        ok,detail=v.check(np.radians(q),np.radians(new));assert ok
        demo.append({'from':q.tolist(),'to':new.tolist(),'distance_remaining_before':d,'status':'Reached' if d<=10+1e-9 else 'Advanced','validation':detail});q=new
    blocking=next(r for r in main['rounds'] if any(e['phase']=='Connect' and e['status']=='Trapped' for e in main['events'][r['event_start']:r['event_end']]))
    report={'status':'passed','runs':len(runs),'seeds':30,'budget_unit':'whole-edge motion validation calls, including every Connect substep','budget_each':1500,'uniform_sampling_both':True,'main_path_min_certified_clearance_m':min(lower),'blocking_round':blocking['round'],'arithmetic_demo':{'from':demo_from,'target':demo_target,'steps':demo},'stats':{}}
    for kind in ['single','connect']:
        rr=[r for r in runs if r['algorithm']==kind];ok=[r for r in rr if r['found']]
        report['stats'][kind]={'success':len(ok),'trials':30,'median_motion_checks_all_trials':float(np.median([r['motion_checks'] for r in rr])),'median_path_length_degrees_successes':float(np.median([r['path_length_degrees'] for r in ok])),'median_outer_rounds_all_trials':float(np.median([r['outer_rounds'] for r in rr]))}
    (A/'connect_run.json').write_text(json.dumps(main,ensure_ascii=False,indent=2))
    (A/'comparison.json').write_text(json.dumps(runs,ensure_ascii=False))
    (Q/'algorithm_validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print('MAIN',main['outer_rounds'],main['motion_checks'],main['path_length_degrees'],'blocked round',blocking['round'],flush=True)
if __name__=='__main__':main()
