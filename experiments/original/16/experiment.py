"""Episode16: static point robot, inflated circular obstacles, reproducible APF trials."""
import json,math
from pathlib import Path
import numpy as np
B=Path(__file__).parent;QA=B/'qa';QA.mkdir(exist_ok=True)
OBS=np.array([[2.,.6],[2.,-.6]]);RAD=.4;GOAL=np.array([5.,0.]);START=np.array([.4,.03]);ETA=2.1444572361897034;RHO0=1.5;KA=1.
LOW=np.array([-.5,-2.6]);HIGH=np.array([5.6,2.6])
COUNTS=0
def clear(p):return float(np.min(np.linalg.norm(OBS-p,axis=1)-RAD))
def edge(a,b):
 global COUNTS
 COUNTS+=1;d=b-a;t=np.clip(np.sum((OBS-a)*d,axis=1)/max(np.dot(d,d),1e-18),0,1);dist=np.linalg.norm(OBS-(a+t[:,None]*d),axis=1)-RAD
 return bool(np.min(dist)>1e-5 and np.all(b>=LOW) and np.all(b<=HIGH))
def forces(p,goal=GOAL):
 v=p-OBS;r=np.linalg.norm(v,axis=1);rho=r-RAD
 if np.min(rho)<=0:raise ValueError('collision')
 a=KA*(goal-p);rep=np.zeros(2)
 for i in range(2):
  if rho[i]<RHO0:rep+=ETA*(1/rho[i]-1/RHO0)/rho[i]**2*v[i]/r[i]
 return a,rep,a+rep

def potential(p,goal=GOAL):
 rho=np.linalg.norm(p-OBS,axis=1)-RAD
 if np.min(rho)<=0:return float('inf')
 return float(.5*KA*np.dot(p-goal,p-goal)+np.sum(.5*ETA*np.maximum(1/rho-1/RHO0,0)**2))
def rrt_connect(seed=16,budget=6000):
 global COUNTS
 rng=np.random.default_rng(seed);trees=[([START.copy()],[-1]),([GOAL.copy()],[-1])];base=COUNTS
 def extend(tree,target):
  pts,par=tree;near=int(np.argmin(np.linalg.norm(np.array(pts)-target,axis=1)));d=target-pts[near];n=np.linalg.norm(d)
  p=pts[near]+d*min(1,.24/max(n,1e-15))
  if n<1e-8:return near,True
  if not edge(pts[near],p):return None,False
  pts.append(p);par.append(near);return len(pts)-1,n<=.24
 def back(t,j):
  p=[]
  while j>=0:p.append(t[0][j]);j=t[1][j]
  return p[::-1]
 turn=0
 while COUNTS-base<budget:
  i=turn%2;j=1-i;sample=rng.uniform(LOW,HIGH);na,_=extend(trees[i],sample)
  if na is not None:
   while COUNTS-base<budget:
    nb,reached=extend(trees[j],trees[i][0][na])
    if nb is None:break
    if reached:
     p1=back(trees[i],na);p2=back(trees[j],nb)
     path=p1+p2[-2::-1] if i==0 else p2+p1[-2::-1]
     return np.array(path),COUNTS-base
  turn+=1
 raise RuntimeError('RRT budget exhausted')

def run(mode='baseline',seed=16,budget=2400):
 global COUNTS
 rng=np.random.default_rng(seed);p=START.copy();hist=[p.copy()];events=[];perturbs=0;tmp=False;subindex=0;count0=COUNTS;route=None;rrt_calls=0
 if mode=='global':route,rrt_calls=rrt_connect(seed)
 goals=[np.array([.8,-2.2]),np.array([3.6,-2.2]),GOAL]
 for k in range(budget):
  if np.linalg.norm(p-GOAL)<.07:status='reached';break
  g=GOAL
  if mode=='subgoal' and tmp:
   g=goals[subindex]
   if np.linalg.norm(p-g)<.14:
    subindex+=1
    if subindex>=len(goals):g=GOAL;tmp=False
    else:g=goals[subindex]
  if mode=='global':
   if subindex<len(route)-1 and np.linalg.norm(p-route[subindex])<.13:subindex+=1
   g=route[min(subindex,len(route)-1)]
  a,r,f=forces(p,g);step=.035*f
  if np.linalg.norm(step)>.075:step*=.075/np.linalg.norm(step)
  accepted=False
  for back in range(12):
   cand=p+step
   if edge(p,cand) and potential(cand,g)<=potential(p,g)+1e-10:accepted=True;break
   step*=.5
  if accepted:p=cand
  hist.append(p.copy())
  stuck=k>70 and np.max(np.linalg.norm(np.array(hist[-60:])-p,axis=1))<.003
  if stuck:
   events.append({'step':k,'kind':'stagnation','position':p.tolist()})
   if mode=='baseline':status='stagnated';break
   if mode=='random':
    jumped=False
    for _ in range(50):
     perturbs+=1;v=rng.uniform(-1,1,2);v*=min(1,.95/max(np.linalg.norm(v),1e-12));cand=p+v
     if edge(p,cand):p=cand;jumped=True;hist.append(p.copy());events.append({'step':k,'kind':'perturb','position':p.tolist()});break
    if perturbs>=200 or not jumped:status='escape_budget_exhausted';break
   if mode=='subgoal':
    if tmp:status='subgoal_stagnated';break
    tmp=True;subindex=0;events.append({'step':k,'kind':'temporary_goals_enabled'})
   if mode=='global':
    # Verified route fallback; do not claim APF always tracks every RRT waypoint.
    events.append({'step':k,'kind':'verified_route_fallback'})
    left=route[subindex:]
    if len(left) and edge(p,left[0]):
     for q in left:
      prev=p.copy();n=max(1,math.ceil(np.linalg.norm(q-prev)/.04))
      for u in np.linspace(0,1,n+1)[1:]:hist.append(prev*(1-u)+q*u)
      p=q.copy()
     status='reached_verified_route';break
    status='fallback_connection_failed';break
 else:status='iteration_budget_exhausted'
 arr=np.array(hist);valid=all(edge(a,b) for a,b in zip(arr,arr[1:]));length=float(np.sum(np.linalg.norm(np.diff(arr,axis=0),axis=1)))
 return dict(mode=mode,seed=seed,status=status,iterations=k+1,path=arr.tolist(),events=events,length_m=length,min_vertex_clearance_m=min(clear(x) for x in arr),goal_distance_m=float(np.linalg.norm(p-GOAL)),all_edges_collision_free=valid,motion_checks_including_validation=COUNTS-count0,rrt_checks=rrt_calls,perturb_attempts=perturbs)

def main():
 global COUNTS
 out=[]
 for mode in ['baseline','random','subgoal','global']:
  seeds=[1,7,16] if mode in ['random','global'] else [16]
  for seed in seeds:
   COUNTS=0;r=run(mode,seed);out.append(r);print(mode,seed,r['status'],round(r['length_m'],3),r['iterations'],flush=True)
 h=1e-5;p=np.array([.7,.2]);grad=np.array([(potential(p+np.eye(2)[i]*h)-potential(p-np.eye(2)[i]*h))/(2*h) for i in range(2)])
 err=float(np.max(np.abs(grad+forces(p)[2])));assert err<1e-5
 assert all(x['all_edges_collision_free'] for x in out)
 data=dict(model='static 2D point; inflated disks; 3D rendering is visualization only',parameters=dict(obstacles=OBS.tolist(),inflated_radius_m=RAD,goal=GOAL.tolist(),start=START.tolist(),k_a=KA,k_r=ETA,rho0_m=RHO0,step_gain=.035,max_step_m=.075,iteration_budget=2400),gradient_finite_difference_error=err,runs=out,scope='Constructed teaching example; no hardware and no universal success/performance ranking')
 (QA/'experiment.json').write_text(json.dumps(data,ensure_ascii=False,indent=2));print('EXPERIMENT SAVED',flush=True)
if __name__=='__main__':main()
