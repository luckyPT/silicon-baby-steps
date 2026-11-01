"""Point-robot discretizations of CHOMP and STOMP mechanisms.
Fixed endpoints; acceleration metric; arc-length obstacle integral evaluated
with 5-point Gaussian quadrature. No physical execution. STOMP uses the
paper's per-index probability weighting and column-normalized covariance
smoother; an explicit descent acceptance check is an engineering addition.
"""
from pathlib import Path
import json,time
import numpy as np
B=Path(__file__).resolve().parent;Q=B/'qa';Q.mkdir(exist_ok=True)
OBS=np.array([[1.6,-.65],[2.55,.75],[3.65,-.55]]);RAD=np.array([.45,.5,.45])
N=41;M=N-2;EPS=.30;WOBS=35.;WS=1.;ITERS=140;K=32
u,w=np.polynomial.legendre.leggauss(5);U=(u+1)/2;W=w/2
D2=np.zeros((M,N))
for i in range(M):D2[i,i:i+3]=[1,-2,1]
DI=D2[:,1:-1];A=DI.T@DI;AI=np.linalg.inv(A)
SMOOTHER=AI/(M*np.max(AI,axis=0)[None,:]);CHOL=np.linalg.cholesky(AI/np.max(np.diag(AI)))
def resample(p,n=N):
 p=np.asarray(p,float);s=np.r_[0,np.cumsum(np.linalg.norm(np.diff(p,axis=0),axis=1))];t=np.linspace(0,s[-1],n)
 return np.column_stack([np.interp(t,s,p[:,j]) for j in range(2)])
def potential(p,obs=OBS,rad=RAD):
 dv=p[...,None,:]-obs;rr=np.linalg.norm(dv,axis=-1);dist=rr-rad;j=np.argmin(dist,axis=-1);d=np.take_along_axis(dist,j[...,None],-1)[...,0]
 grad=np.take_along_axis(dv,j[...,None,None],axis=-2)[...,0,:]/np.maximum(1e-12,np.take_along_axis(rr,j[...,None],-1)[...,0])[...,None]
 c=np.where(d<0,-d+EPS/2,np.where(d<EPS,(d-EPS)**2/(2*EPS),0))
 cp=np.where(d<0,-1,np.where(d<EPS,(d-EPS)/EPS,0));return c,cp[...,None]*grad
def cost(p,obs=OBS,rad=RAD,gradient=False):
 p=np.asarray(p);d=np.diff(p,axis=-2);length=np.linalg.norm(d,axis=-1);v=d/np.maximum(length[...,None],1e-12)
 probes=p[...,:-1,None,:]+d[...,None,:]*U[:,None];c,cg=potential(probes,obs,rad)
 avg=np.sum(c*W,axis=-1);edge=length*avg;dd=np.einsum('ij,...jk->...ik',D2,p);js=.5*np.sum(dd*dd,axis=(-2,-1));jo=np.sum(edge,axis=-1)
 # Per-index state costs distribute each arc segment equally to its two ends.
 stage=np.zeros(p.shape[:-1]);stage[...,:-1]+=.5*WOBS*edge;stage[...,1:]+=.5*WOBS*edge
 if not gradient:return WS*js+WOBS*jo,js,jo,stage
 g=WS*np.einsum('ji,...jk->...ik',D2,dd)
 ga=-v*avg[...,None]+length[...,None]*np.sum(cg*(W*(1-U))[:,None],axis=-2)
 gb=v*avg[...,None]+length[...,None]*np.sum(cg*(W*U)[:,None],axis=-2)
 g[...,:-1,:]+=WOBS*ga;g[...,1:,:]+=WOBS*gb
 return float(WS*js+WOBS*jo),float(js),float(jo),g
def segment_clearance(p,obs=OBS,rad=RAD):
 a=p[:-1];d=np.diff(p,axis=0);proj=np.sum((obs[None,:,:]-a[:,None,:])*d[:,None,:],axis=-1)/np.maximum(1e-15,np.sum(d*d,axis=-1))[:,None]
 closest=a[:,None,:]+np.clip(proj,0,1)[...,None]*d[:,None,:]
 return float(np.min(np.linalg.norm(closest-obs[None,:,:],axis=-1)-rad))
def metrics(p,obs=OBS,rad=RAD):
 j,s,o,_=cost(p,obs,rad);clear=segment_clearance(p,obs,rad)
 return dict(cost=float(j),smooth=float(s),obstacle=float(o),length_m=float(np.linalg.norm(np.diff(p,axis=0),axis=1).sum()),min_clearance_m=clear,certified=bool(clear>1e-6))
def chomp(initial,obs=OBS,rad=RAD,iters=ITERS):
 p=initial.copy();hist=[];evals=0;start=time.perf_counter()
 for it in range(iters+1):
  j,s,o,g=cost(p,obs,rad,True);evals+=1;hist.append(dict(iteration=it,path=p.tolist(),**metrics(p,obs,rad)))
  if it==iters:break
  direction=AI@g[1:-1];mx=np.max(np.linalg.norm(direction,axis=1));direction*=min(1,.16/max(1e-12,mx));alpha=1.;accepted=False
  for _ in range(16):
   trial=p.copy();trial[1:-1]-=alpha*direction;jnew=cost(trial,obs,rad)[0];evals+=1
   if jnew<j-1e-12:p=trial;accepted=True;break
   alpha*=.5
  if not accepted:
   hist[-1]['stalled']=True;break
 return dict(method='CHOMP point-robot discretization',history=hist,final=metrics(p,obs,rad),cost_evaluations=evals,elapsed_s=time.perf_counter()-start)
def stomp(initial,seed,obs=OBS,rad=RAD,iters=ITERS,sigma=.30):
 rng=np.random.default_rng(seed);p=initial.copy();hist=[];evals=0;start=time.perf_counter();rollout_demo=None
 for it in range(iters+1):
  hist.append(dict(iteration=it,path=p.tolist(),**metrics(p,obs,rad)))
  if it==iters:break
  eps=np.zeros((K,N,2));eps[:,1:-1,:]=sigma*np.einsum('ij,kjl->kil',CHOL,rng.normal(size=(K,M,2)))
  noisy=p[None,:,:]+eps;tot,_,_,stage=cost(noisy,obs,rad);evals+=K
  ss=stage[:,1:-1];lo=ss.min(axis=0);span=ss.max(axis=0)-lo;z=np.divide(ss-lo,span[None,:],out=np.zeros_like(ss),where=span[None,:]>1e-12)
  prob=np.exp(-10*z);prob/=prob.sum(axis=0,keepdims=True)
  raw=np.sum(prob[...,None]*eps[:,1:-1,:],axis=0);delta=SMOOTHER@raw
  # Descent check does not certify collision freedom: final segments are checked separately.
  old=float(cost(p,obs,rad)[0]);evals+=1;alpha=1.;accepted=False
  for _ in range(10):
   trial=p.copy();trial[1:-1]+=alpha*delta;jnew=float(cost(trial,obs,rad)[0]);evals+=1
   if jnew<old-1e-12:p=trial;accepted=True;break
   alpha*=.5
  hist[-1].update(accepted=accepted,mean_update_norm=float(np.linalg.norm(delta)),noise_sigma=sigma)
  if it==0:
   rollout_demo=dict(paths=noisy[:8].tolist(),total_costs=tot[:8].tolist(),weights_at_middle=prob[:,M//2].tolist(),raw_delta=raw.tolist(),smoothed_delta=delta.tolist())
 return dict(method='STOMP point-robot discretization with explicit descent acceptance',seed=seed,history=hist,final=metrics(p,obs,rad),cost_evaluations=evals,rollout_demo=rollout_demo,elapsed_s=time.perf_counter()-start)
def main():
 prior=json.loads((B/'assets/initial_route.json').read_text());initial=resample(prior['vertices'])
 # Directional finite-difference check of the actual discretized obstacle integral.
 rng=np.random.default_rng(123);probe=initial.copy();probe[1:-1]+=rng.normal(size=(M,2))*.021;d=rng.normal(size=probe.shape);d[[0,-1]]=0
 j,_,_,g=cost(probe,gradient=True);h=1e-6;fd=(cost(probe+h*d)[0]-cost(probe-h*d)[0])/(2*h);analytic=float(np.sum(g*d));assert abs(fd-analytic)<1e-5,(fd,analytic)
 results=dict(scope='Static 2D point robot; fixed endpoints and parameter grid; not a complete robot/paper benchmark',parameters=dict(points=N,internal_variables=2*M,iterations=ITERS,rollouts_per_iteration=K,epsilon_m=EPS,obstacle_weight=WOBS,smoothness_weight=WS,stomp_h=10,stomp_sigma_m=.30,quadrature_points=5),obstacles=OBS.tolist(),radii=RAD.tolist(),initial_path=initial.tolist(),initial_metrics=metrics(initial),chomp=chomp(initial),stomp=[stomp(initial,s) for s in [1,7,17]],gradient_check=dict(finite_difference=fd,analytic=analytic,abs_error=abs(fd-analytic)))
 obs=np.array([[2.5,0.]]);rad=np.array([.65]);straight=np.column_stack([np.linspace(0,5,N),np.zeros(N)])
 results['symmetry_failure']=dict(obstacles=obs.tolist(),radii=rad.tolist(),initial_path=straight.tolist(),chomp=chomp(straight,obs,rad,iters=80),stomp=[stomp(straight,s,obs,rad,iters=160,sigma=.55) for s in [1,7,17]])
 upper=straight.copy();upper[:,1]=1.05*np.sin(np.linspace(0,np.pi,N));lower=upper.copy();lower[:,1]*=-1;average=(upper+lower)/2
 results['averaging_counterexample']=dict(obstacles=obs.tolist(),radii=rad.tolist(),upper=upper.tolist(),lower=lower.tolist(),average=average.tolist(),upper_clearance=segment_clearance(upper,obs,rad),lower_clearance=segment_clearance(lower,obs,rad),average_clearance=segment_clearance(average,obs,rad))
 assert results['averaging_counterexample']['upper_clearance']>0 and results['averaging_counterexample']['lower_clearance']>0 and results['averaging_counterexample']['average_clearance']<0
 for family in [results,results['symmetry_failure']]:
  init=np.array(family['initial_path'])
  for rr in [family['chomp'],*family['stomp']]:
   for hh in rr['history']:assert np.allclose(np.array(hh['path'])[[0,-1]],init[[0,-1]])
   cs=[hh['cost'] for hh in rr['history']];assert np.max(np.diff(cs),initial=0)<1e-8
 (Q/'experiment.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
 print('INITIAL',results['initial_metrics'])
 for name,family in [('main',results),('symmetry',results['symmetry_failure'])]:
  for rr in [family['chomp'],*family['stomp']]:print(name,rr['method'],rr.get('seed'),rr['final'],'iterations',len(rr['history'])-1,flush=True)
 print('GRADIENT CHECK',results['gradient_check'],flush=True)
if __name__=='__main__':main()
