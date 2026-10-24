"""Episode12: scalar time scaling of the SAME accepted Episode11 path.
Progress s is dimensionless; speed and acceleration are NOT joint limits.
The dense path table interpolates points on the original Bezier/line geometry.
"""
from pathlib import Path
import numpy as np,json,math
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
def profile(distance=1.,vmax=.25,amax=.125):
 vp=min(vmax,math.sqrt(distance*amax));ta=vp/amax;tc=max(0,(distance-vp*ta)/vp)
 return {'distance':distance,'vmax':vmax,'amax':amax,'vp':vp,'ta':ta,'tc':tc,'T':2*ta+tc,'kind':'trapezoid' if tc>1e-10 else 'triangle'}
FULL=profile();SHORT=profile(.25)
def scalar(t,p=FULL):
 t=np.asarray(t,dtype=float);a=p['amax'];v=p['vp'];ta=p['ta'];tc=p['tc'];T=p['T'];D=p['distance']
 x=np.where(t<ta,.5*a*t*t,np.where(t<ta+tc,.5*a*ta*ta+v*(t-ta),D-.5*a*(T-t)**2))
 vel=np.where(t<ta,a*t,np.where(t<ta+tc,v,a*(T-t)))
 acc=np.where(t<ta,a,np.where(t<ta+tc,0.,-a))
 x=np.where(t<0,0,np.where(t>=T,D,x));vel=np.where((t<0)|(t>=T),0,vel);acc=np.where((t<0)|(t>=T),0,acc)
 return x,vel,acc
def uniform(t,T=6.):
 t=np.asarray(t);return np.clip(t/T,0,1),np.where((t>=0)&(t<T),1/T,0.),np.zeros_like(t,dtype=float)
