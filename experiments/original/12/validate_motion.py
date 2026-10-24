from pathlib import Path
import sys,json,hashlib,numpy as np
from motion import FULL,SHORT,scalar,q_at,arc,PREVIOUS
B=Path(__file__).resolve().parent
sys.path.insert(0,str(B.parent/'10'))
from rrt import clearances
r={'status':'passed','progress_units':'dimensionless s; v in 1/s; a in 1/s^2','original_path_source':'Episode11 accepted_blend_alpha_0_25','path_source_sha256':hashlib.sha256((B/'qa/postprocess_validation.json').read_bytes()).hexdigest(),'path_length_deg':float(arc[-1]),'profiles':{}}
assert abs(arc[-1]-PREVIOUS['metrics']['accepted_blend_alpha_0_25']['length_deg'])<1e-6
for name,p in [('full',FULL),('short_prefix',SHORT)]:
 t=np.linspace(0,p['T'],200001);x,v,a=scalar(t,p);assert abs(x[0])<1e-12 and abs(x[-1]-p['distance'])<1e-12
 assert v[0]==v[-1]==0 and np.min(np.diff(x))>=-1e-12 and v.max()<=p['vmax']+1e-12 and np.abs(a).max()<=p['amax']+1e-12
 assert abs(np.trapezoid(v,t)-p['distance'])<1e-9
 for tt in [p['ta'],p['ta']+p['tc']]:
  l=scalar(tt-1e-9,p);rr=scalar(tt+1e-9,p);assert abs(l[0]-rr[0])<1e-8 and abs(l[1]-rr[1])<1e-8
 q=q_at(x);cs=clearances(np.radians(q));assert cs.min()>.015 and np.abs(q).max()<=150+1e-10
 assert np.allclose(q[0],[-30,90]) and np.allclose(q[-1],q_at(p['distance']))
 r['profiles'][name]={**p,'area':float(np.trapezoid(v,t)),'sampled_min_clearance_m':float(cs.min()),'endpoint_q_deg':q[-1].tolist(),'same_geometry':True,'scalar_bounds_checked':True}
assert FULL['T']==6. and FULL['ta']==FULL['tc']==2.
assert SHORT['tc']==0 and abs(SHORT['T']-2.8284271247461903)<1e-12
r['scope']=['Kinematic teaching time law, not a real controller run.','Uniform comparator has ideal velocity jumps; not executable under finite acceleration.','Joint velocity/acceleration, dynamics, tracking and liquid stability are NOT certified here.','Short case ends at 25% of the full route and is not a same-task speed comparison.','Original path is tangent-continuous at joins, not guaranteed C2; S-curve timing alone will not repair path curvature jumps.']
(B/'qa/motion_validation.json').write_text(json.dumps(r,ensure_ascii=False,indent=2));print(json.dumps(r,ensure_ascii=False,indent=2))
