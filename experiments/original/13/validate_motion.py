from pathlib import Path
import json,sys,hashlib
import numpy as np
from motion import *
B=Path(__file__).resolve().parent;sys.path.insert(0,str(B.parent/'10'))
from rrt import clearances
r={'status':'passed','progress_units':'s dimensionless, v 1/s, a 1/s^2, j 1/s^3','same_path_as_episode12':True,'path_source_sha256':hashlib.sha256((B/'qa/postprocess_validation.json').read_bytes()).hexdigest(),'profiles':{}}
assert np.allclose(BOUNDS[-1],[1,0,0],atol=1e-13)
for mode,p in [('trap',TRAP),('s',SCURVE)]:
 t=np.linspace(0,p['T'],200001);s,v,a,j=law(t,mode)
 assert abs(s[0])<1e-12 and abs(s[-1]-1)<1e-12 and v[0]==v[-1]==0
 assert np.min(np.diff(s))>=-1e-12 and v.max()<=.25+1e-12 and abs(a).max()<=.125+1e-12
 assert abs(np.trapezoid(v,t)-1)<1e-9
 q=q_at(s);cs=clearances(np.radians(q));assert cs.min()>.015 and abs(q).max()<=150+1e-9
 r['profiles'][mode]={**p,'area':float(np.trapezoid(v,t)),'min_clearance_m':float(cs.min()),'q_start_deg':q[0].tolist(),'q_end_deg':q[-1].tolist()}
 if mode=='s':
  assert a[0]==a[-1]==0 and abs(j).max()<=.125+1e-12
  for x in range(8):
   left=law(x-1e-9)[0:3];right=law(x+1e-9)[0:3];assert np.max(abs(np.array(left)-right))<1e-8
  # Independent finite difference and quadrature checks inside all seven phases.
  for x in np.linspace(.1,6.9,130):
   if min(abs(x-k) for k in range(8))<.01:continue
   h=1e-5;lo=law(x-h);hi=law(x+h);mid=law(x)
   for k in range(3):assert abs((hi[k]-lo[k])/(2*h)-mid[k+1])<1e-7
  assert np.allclose([s_curve(3)[0],s_curve(4)[0]-s_curve(3)[0],1-s_curve(4)[0]],[.375,.25,.375])
  r['profiles'][mode].update(jerk_bounded=True,position_velocity_acceleration_continuous=True,phase_duration_seconds=[1]*7,phase_jerks=JERKS.tolist(),phase_end_states=BOUNDS.tolist())
def derivatives(part,u):
 p=np.array(part['controls_deg']);v=p[1]-p[0] if part['kind']=='line' else 2*((1-u)*(p[1]-p[0])+u*(p[2]-p[1]));a=np.zeros(2) if part['kind']=='line' else 2*(p[2]-2*p[1]+p[0]);n=np.linalg.norm(v)
 return arc[-1]*v/n,arc[-1]**2*(a/n**2-v*np.dot(v,a)/n**4)
joins=[]
for i,(p,q) in enumerate(zip(PARTS,PARTS[1:])):
 v1,a1=derivatives(p,1);v2,a2=derivatives(q,0);assert np.linalg.norm(v1-v2)<1e-8
 joins.append({'progress':float(join_progress()[i]),'tangent_jump_deg_per_progress':float(np.linalg.norm(v1-v2)),'curvature_related_qss_jump':float(np.linalg.norm(a1-a2))})
assert max(x['curvature_related_qss_jump'] for x in joins)>1
r['geometric_joins']=joins
r['scope']=['Only scalar path progress time scaling is jerk-limited.','The original path has curvature discontinuities; joint acceleration continuity is not certified.','No artificial vibration, liquid simulation or hardware stability claim.','S-curve jerk is piecewise constant with finite jumps, not continuous jerk.','6s versus 7s only for this exact set of parameters; no general fixed-time penalty claim.']
(B/'qa/motion_validation.json').write_text(json.dumps(r,ensure_ascii=False,indent=2));print(json.dumps(r,ensure_ascii=False,indent=2))
