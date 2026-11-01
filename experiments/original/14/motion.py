"""Same accepted path; map the Episode13 7s S-time-law to joint derivatives.
Teaching joint limits are checked, followed by a uniform 1.5x time dilation.
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

# Episode14 teaching limits: deliberately specified as example limits, not hardware data.
VLIMIT=np.array([12.,12.]) # deg/s
ALIMIT=np.array([20.,20.]) # deg/s^2
TABLES=[];cursor=0.
for part in PARTS:
 p=np.array(part['controls_deg']);u=np.linspace(0,1,40001);z=u[:,None]
 q=(1-z)*p[0]+z*p[1] if part['kind']=='line' else (1-z)**2*p[0]+2*z*(1-z)*p[1]+z*z*p[2]
 ds=np.r_[0,np.cumsum(np.linalg.norm(np.diff(q,axis=0),axis=1))]
 TABLES.append((cursor+ds,u));cursor+=ds[-1]
LENGTH=cursor;JOINS=np.array([x[0][-1]/LENGTH for x in TABLES[:-1]])
def path_derivatives(s,side='right'):
 s=np.clip(np.asarray(s,dtype=float),0,1)
 for join in JOINS:s=np.where(abs(s-join)<1e-12,join,s)
 k=np.searchsorted(JOINS,s,side=side)
 shape=s.shape;qout=np.zeros(shape+(2,));qs=np.zeros_like(qout);qss=np.zeros_like(qout)
 for i,part in enumerate(PARTS):
  mask=k==i
  if not np.any(mask):continue
  p=np.array(part['controls_deg']);dist,uu=TABLES[i];u=np.interp(s[mask]*LENGTH,dist,uu)[:,None]
  if part['kind']=='line':q=(1-u)*p[0]+u*p[1];d=np.broadcast_to(p[1]-p[0],q.shape);dd=np.zeros_like(q)
  else:q=(1-u)**2*p[0]+2*u*(1-u)*p[1]+u*u*p[2];d=2*((1-u)*(p[1]-p[0])+u*(p[2]-p[1]));dd=np.broadcast_to(2*(p[2]-2*p[1]+p[0]),q.shape)
  n=np.linalg.norm(d,axis=-1,keepdims=True)
  qout[mask]=q;qs[mask]=LENGTH*d/n;qss[mask]=LENGTH**2*(dd/n**2-d*np.sum(d*dd,axis=-1,keepdims=True)/n**4)
 return qout,qs,qss
def joint_state(t,stretch=1.,side='right'):
 s,v,a,j=s_curve(np.asarray(t)/stretch);q,qs,qss=path_derivatives(s,side)
 qv=qs*(v/stretch)[...,None];qa=qss*(v/stretch)[...,None]**2+qs*(a/stretch**2)[...,None]
 return q,qv,qa,s,v/stretch,a/stretch**2
