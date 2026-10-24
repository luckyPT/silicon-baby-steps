"""Episode 11 geometry evidence. Angles stored/displayed in degrees.

Reuses episode 10 seed 7 path; no planner rerun or environment modification.
Local quadratic Bezier corner blend is a teaching implementation, not OMPL.
"""
from pathlib import Path
import sys, json, math, hashlib
import numpy as np
from scipy.integrate import quad

B=Path(__file__).resolve().parent
PREV=B.parent/'10'
sys.path.insert(0,str(PREV))
from rrt import clearances, MotionValidator
from arm_model import clearance

def segment(kind, points):
    return {'kind':kind,'controls_deg':np.asarray(points).tolist()}

def value(s,u):
    p=np.array(s['controls_deg']);u=np.asarray(u)[...,None]
    if s['kind']=='line':return (1-u)*p[0]+u*p[1]
    return (1-u)**2*p[0]+2*(1-u)*u*p[1]+u*u*p[2]

def derivative(s,u):
    p=np.array(s['controls_deg'])
    if s['kind']=='line':return p[1]-p[0]
    return 2*((1-u)*(p[1]-p[0])+u*(p[2]-p[1]))

def polyline(p):return [segment('line',[a,b]) for a,b in zip(p,p[1:])]

def fillet(p,alpha):
    # This episode's simplified path has exactly one interior corner.
    assert len(p)==3
    a,b,c=np.asarray(p);left=b+alpha*(a-b);right=b+alpha*(c-b)
    return [segment('line',[a,left]),segment('quadratic_bezier',[left,b,right]),segment('line',[right,c])]

def validate(parts):
    length=sum(quad(lambda u:np.linalg.norm(derivative(s,u)),0,1,epsabs=1e-10)[0] for s in parts)
    min_c=math.inf;lower=math.inf;worst=None;all_inside=True
    for s in parts:
        # 20,001 evaluations per primitive and a model-specific derivative
        # displacement bound between evaluations, including curve interiors.
        n=20000;u=np.linspace(0,1,n+1);q=value(s,u)
        cs=clearances(np.radians(q));k=int(cs.argmin())
        if cs[k]<min_c:min_c=float(cs[k]);worst=q[k].tolist()
        d0=np.abs(derivative(s,0));d1=np.abs(derivative(s,1))
        maxd=np.maximum(d0,d1)*math.pi/180
        interval_displacement=(2*maxd[0]+maxd[1])/n
        lower=min(lower,float(cs.min()-interval_displacement))
        # Bezier convex hull is inside joint limits if all controls are inside.
        all_inside=all_inside and bool(np.max(np.abs(s['controls_deg']))<=150+1e-10)
        # Independent scalar geometry cross-check at every 20th dense sample.
        scalar=np.array([clearance(x) for x in q[::20]])
        assert np.max(np.abs(scalar-cs[::20]))<1e-12
    return {'length_deg':length,'sampled_min_clearance_m':min_c,
            'model_clearance_lower_bound_m':lower,'critical_q_deg':worst,
            'joint_limits_valid':all_inside,'collision_free_in_model':bool(lower>0 and all_inside),
            'meets_episode_10mm_margin':bool(lower>=.01 and all_inside)}

def main():
    source=PREV/'assets/informed_run.json';run=json.loads(source.read_text());p=np.array(run['best_path'])
    assert run['seed']==7 and len(p)==5
    oracle=MotionValidator();out=[p[0]];i=0;attempts=[]
    while i<len(p)-1:
        for j in range(len(p)-1,i,-1):
            ok,detail=oracle.check(np.radians(p[i]),np.radians(p[j]))
            attempts.append({'from_original_vertex':i,'to_original_vertex':j,'accepted':ok,'validation':detail})
            if ok:break
        out.append(p[j]);i=j
    out=np.array(out);assert len(out)==3
    paths={'original':polyline(p),'shortcut':polyline(out),
           'aggressive_blend_alpha_0_5':fillet(out,.5),
           'accepted_blend_alpha_0_25':fillet(out,.25),
           'unsafe_direct':polyline(p[[0,-1]])}
    metrics={k:validate(v) for k,v in paths.items()}
    assert metrics['original']['collision_free_in_model']
    assert metrics['shortcut']['collision_free_in_model']
    assert not metrics['aggressive_blend_alpha_0_5']['collision_free_in_model']
    assert metrics['accepted_blend_alpha_0_25']['meets_episode_10mm_margin']
    assert not metrics['unsafe_direct']['collision_free_in_model']
    for v in paths.values():
        assert np.allclose(value(v[0],0),p[0]) and np.allclose(value(v[-1],1),p[-1])
        for a,b in zip(v,v[1:]):assert np.allclose(value(a,1),value(b,0))
    good=paths['accepted_blend_alpha_0_25']
    for a,b in zip(good,good[1:]):
        da=derivative(a,1);db=derivative(b,0)
        assert abs(np.cross(da,db))<1e-8 and np.dot(da,db)>0
    report={'status':'passed','source':'episode10 Informed RRT* seed 7 best_path',
            'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
            'original_vertices_deg':p.tolist(),'shortcut_vertices_deg':out.tolist(),
            'attempts':attempts,'paths':paths,'metrics':metrics,
            'length_reduction_percent':100*(1-metrics['accepted_blend_alpha_0_25']['length_deg']/metrics['original']['length_deg']),
            'notes':['No time parameterization or dynamics simulation.',
                     '10 mm margin is an episode teaching threshold, not a universal engineering safety standard.',
                     'Clearance lower bound is specific to this planar 2R capsule-disc model.',
                     'Curve joins preserve tangent direction, not a supplied time law or acceleration continuity.']}
    (B/'qa/postprocess_validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print(json.dumps({'metrics':metrics,'reduction_percent':report['length_reduction_percent']},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
