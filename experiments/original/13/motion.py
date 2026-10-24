"""Same accepted path; compare 6s trapezoid and 7s finite-jerk scalar time law.
All limits refer to dimensionless path progress, not per-axis constraints.
"""
from pathlib import Path
import numpy as np,json
B=Path(__file__).resolve().parent
PREVIOUS=json.loads((B/'qa/postprocess_validation.json').read_text())
PARTS=PREVIOUS['paths']['accepted_blend_alpha_0_25']
Q=[]
for part in PARTS:
 p=np.array(part['controls_deg']);u=np.linspace(0,1,10001)[:,None]
 q=(1-u)*p[0]+u*p[1] if part['kind']=='line' else (1-u)**2*p[0]+2*u*(1-u)*p[1]+u*u*p[2]
 Q.extend(q if not Q else q[1:])
Q=np.array(Q);arc=np.r_[0,np.cumsum(np.linalg.norm(np.diff(Q,axis=0),axis=1))];S=arc/arc[-1]
def q_at(s):
 s=np.asarray(s);return np.stack([np.interp(np.clip(s,0,1),S,Q[:,i]) for i in range(2)],axis=-1)
TRAP={'T':6.,'vmax':.25,'amax':.125,'name':'梯形速度'}
SCURVE={'T':7.,'vmax':.25,'amax':.125,'jmax':.125,'name':'S曲线'}
JERKS=np.array([.125,0,-.125,0,-.125,0,.125])
BOUNDS=[(0.,0.,0.)]
for j in JERKS:
 s,v,a=BOUNDS[-1];BOUNDS.append((s+v+a/2+j/6,v+a+j/2,a+j))
BOUNDS=np.array(BOUNDS)
def trapezoid(t):
 t=np.asarray(t,dtype=float);s=np.where(t<2,.0625*t*t,np.where(t<4,.25+.25*(t-2),1-.0625*(6-t)**2))
 v=np.where(t<2,.125*t,np.where(t<4,.25,.125*(6-t)));a=np.where(t<2,.125,np.where(t<4,0.,-.125))
 outside=(t<0)|(t>=6)
 return np.where(t<0,0,np.where(t>=6,1,s)),np.where(outside,0,v),np.where(outside,0,a)
def s_curve(t):
 t=np.asarray(t,dtype=float);k=np.clip(np.floor(t),0,6).astype(int);u=np.clip(t-k,0,1)
 s0,v0,a0=np.moveaxis(BOUNDS[k],-1,0);j=JERKS[k]
 s=s0+v0*u+a0*u*u/2+j*u**3/6;v=v0+a0*u+j*u*u/2;a=a0+j*u
 outside=(t<0)|(t>=7)
 return np.where(t<0,0,np.where(t>=7,1,s)),np.where(outside,0,v),np.where(outside,0,a),np.where(outside,0,j)
def law(t,mode='s'):
 return s_curve(t) if mode=='s' else (*trapezoid(t),np.zeros_like(np.asarray(t,dtype=float)))
def join_progress():
 # Original line/Bezier joining progress. The evaluator checks curvature on each side.
 lengths=[]
 for p in PARTS:
  z=np.array(p['controls_deg']);u=np.linspace(0,1,10001)[:,None]
  q=(1-u)*z[0]+u*z[1] if p['kind']=='line' else (1-u)**2*z[0]+2*u*(1-u)*z[1]+u*u*z[2]
  lengths.append(np.linalg.norm(np.diff(q,axis=0),axis=1).sum())
 return np.cumsum(lengths)[:-1]/sum(lengths)
