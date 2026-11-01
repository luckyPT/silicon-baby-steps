from pathlib import Path
import json,sys,hashlib
import numpy as np
from scipy.optimize import brentq,minimize_scalar
from scipy.integrate import quad
from motion import *
B=Path(__file__).resolve().parent;sys.path.insert(0,str(B.parent/'10'))
from rrt import clearances
crossings=[brentq(lambda t:s_curve(t)[0]-s,0,7,xtol=1e-14) for s in JOINS]
breaks=sorted(set([float(k) for k in range(8)]+crossings))
def extrema(component,joint):
 candidates=[]
 def value(t,side='right'):return float(joint_state(t,side=side)[component][joint])
 for x in breaks:
  for side in ['left','right']:candidates.append((abs(value(x,side)),x,side))
 for lo,hi in zip(breaks,breaks[1:]):
  ts=np.linspace(lo+1e-10,hi-1e-10,65);vs=np.array([abs(value(t)) for t in ts]);candidates.extend((v,t,'right') for v,t in zip(vs,ts))
  for k in range(1,len(ts)-1):
   if vs[k]>=vs[k-1] and vs[k]>=vs[k+1]:
    opt=minimize_scalar(lambda t:-abs(value(t)),bounds=(ts[k-1],ts[k+1]),method='bounded',options={'xatol':1e-13});candidates.append((-opt.fun,opt.x,'right'))
 m=max(candidates);return {'abs_peak':m[0],'time_seconds':m[1],'side':m[2],'signed_peak':value(m[1],m[2])}
peaks={'velocity':[extrema(1,i) for i in range(2)],'acceleration':[extrema(2,i) for i in range(2)]}
vm=np.array([x['abs_peak'] for x in peaks['velocity']]);am=np.array([x['abs_peak'] for x in peaks['acceleration']])
required=max(np.max(vm/VLIMIT),np.sqrt(np.max(am/ALIMIT)));stretch=1.5
assert required<stretch and vm[1]>VLIMIT[1] and am[0]>ALIMIT[0]
assert vm[0]<VLIMIT[0] and am[1]<ALIMIT[1]
t=np.sort(np.r_[np.linspace(0,7,200001),np.array(crossings)-1e-9,np.array(crossings)+1e-9]);q,v,a,s,*_=joint_state(t)
assert np.allclose(np.max(abs(v),axis=0),vm,atol=2e-6) and np.allclose(np.max(abs(a),axis=0),am,atol=2e-5)
# Independent quadrature + root inversion reference, not the renderer's arclength table.
def deriv(part,u):
 p=np.array(part['controls_deg']);return p[1]-p[0] if part['kind']=='line' else 2*((1-u)*(p[1]-p[0])+u*(p[2]-p[1]))
exact_lengths=np.array([quad(lambda u:np.linalg.norm(deriv(p,u)),0,1,epsabs=1e-11)[0] for p in PARTS]);exact_total=sum(exact_lengths);assert abs(exact_total-LENGTH)<2e-8
def reference(s,side='right'):
 joins=np.cumsum(exact_lengths)[:-1]/exact_total;k=int(np.searchsorted(joins,s,side=side));part=PARTS[k];p=np.array(part['controls_deg']);dist=np.clip(s*exact_total-sum(exact_lengths[:k]),0,exact_lengths[k]);u=0 if dist<1e-12 else 1 if dist>=exact_lengths[k]-1e-12 else brentq(lambda u:quad(lambda x:np.linalg.norm(deriv(part,x)),0,u,epsabs=1e-10)[0]-dist,0,1,xtol=1e-13)
 z=p[0]*(1-u)+p[1]*u if part['kind']=='line' else (1-u)**2*p[0]+2*u*(1-u)*p[1]+u*u*p[2]
 d=deriv(part,u);dd=np.zeros(2) if part['kind']=='line' else 2*(p[2]-2*p[1]+p[0]);n=np.linalg.norm(d)
 return z,exact_total*d/n,exact_total**2*(dd/n**2-d*np.dot(d,dd)/n**4)
for ss in np.linspace(0,1,37):
 for actual,expected in zip(path_derivatives(ss),reference(ss)):assert np.allclose(actual,expected,atol=3e-6,rtol=1e-8)
# Check derivatives against independently sampled q(t), away from all joins and phase boundaries.
for x in np.linspace(.2,6.8,101):
 if min(abs(x-y) for y in breaks)<.01:continue
 h=1e-4;lo=joint_state(x-h);mid=joint_state(x);hi=joint_state(x+h)
 assert np.allclose((hi[0]-lo[0])/(2*h),mid[1],atol=2e-5)
 assert np.allclose((hi[1]-lo[1])/(2*h),mid[2],atol=2e-5)
slow=joint_state(t*stretch,stretch)
assert np.allclose(slow[0],q,atol=1e-10) and np.allclose(slow[1],v/stretch,atol=1e-10) and np.allclose(slow[2],a/stretch**2,atol=1e-10)
assert np.all(np.max(abs(slow[1]),axis=0)<VLIMIT) and np.all(np.max(abs(slow[2]),axis=0)<ALIMIT)
clear=clearances(np.radians(q));assert clear.min()>.015 and abs(q).max()<=150+1e-9
assert np.allclose(v[[0,-1]],0) and np.allclose(a[[0,-1]],0)
joins=[]
for tt in crossings:
 left=joint_state(tt,side='left');right=joint_state(tt,side='right');ss=left[3]
 # Resolve the exact boundary progress to avoid floating point side ambiguity.
 ss=float(JOINS[np.argmin(abs(JOINS-ss))]);v0,a0=s_curve(tt)[1:3]
 ql,qls,qlss=path_derivatives(ss,'left');qr,qrs,qrss=path_derivatives(ss,'right')
 al=qlss*v0*v0+qls*a0;ar=qrss*v0*v0+qrs*a0
 assert np.allclose(ql,qr,atol=1e-8) and np.allclose(qls,qrs,atol=1e-8)
 joins.append({'progress':ss,'base_time':tt,'base_accel_left_deg_s2':al.tolist(),'base_accel_right_deg_s2':ar.tolist(),'slow_accel_left_deg_s2':(al/stretch**2).tolist(),'slow_accel_right_deg_s2':(ar/stretch**2).tolist(),'slow_jump_norm':float(np.linalg.norm(ar-al)/stretch**2)})
assert any(j['slow_jump_norm']>1 for j in joins)
r={'status':'passed','limits_are_hypothetical_teaching_values_not_manufacturer_data':True,'joint_velocity_limits_deg_s':VLIMIT.tolist(),'joint_acceleration_limits_deg_s2':ALIMIT.tolist(),'original_duration':7.,'adjusted_duration':10.5,'stretch_factor':stretch,'required_factor_by_numerical_extrema':float(required),'original_peaks':peaks,'adjusted_peak_velocity_deg_s':(vm/stretch).tolist(),'adjusted_peak_acceleration_deg_s2':(am/stretch**2).tolist(),'original_velocity_pass':(vm<=VLIMIT).tolist(),'original_acceleration_pass':(am<=ALIMIT).tolist(),'adjusted_velocity_pass':[True,True],'adjusted_piecewise_acceleration_amplitude_pass':[True,True],'all_path_joins_checked_on_both_sides':joins,'path_length_deg':float(LENGTH),'min_sampled_clearance_m':float(clear.min()),'same_geometric_path':True,'same_positions_at_same_normalized_progress':True,'independent_arclength_reference':'scipy quadrature + root inversion, 37 sample points','dense_validation_samples':len(t),'scope':['Only joint speed and PIECEWISE acceleration amplitudes pass the teaching limits.','Acceleration is discontinuous at original path curvature joins; classical acceleration there is not defined, both one-sided limits are checked.','Global slowing reduces jump magnitude but never removes it.','Joint jerk, torques, load, tracking, hardware safety and liquid stability are not certified.','No claim of time optimality.'],'path_source_sha256':hashlib.sha256((B/'qa/postprocess_validation.json').read_bytes()).hexdigest()}
(B/'qa/motion_validation.json').write_text(json.dumps(r,ensure_ascii=False,indent=2));print(json.dumps(r,ensure_ascii=False,indent=2))
