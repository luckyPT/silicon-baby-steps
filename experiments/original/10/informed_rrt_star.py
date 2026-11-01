"""RRT* teaching implementation: cumulative cost, parent choice, rewiring.

Internal angles are radians. Both planners share the exact sample prefix until their first solution, metrics, oracle,
steering and goal-connection rules. An oracle-call budget includes every
parent, rewire and goal check. Accepted mutations are atomic on exhaustion.
"""
from pathlib import Path
import json,math,time
import numpy as np
from rrt import START,GOAL,LIMIT,STEP,MotionValidator,clearances,deg

B=Path(__file__).parent;A=B/'assets';Q=B/'qa'
BUDGET=6000
class Exhausted(Exception):pass
class Oracle(MotionValidator):
 def check(self,a,b):
  if self.calls>=self.budget:raise Exhausted()
  return super().check(a,b)

def solve(seed=1,star=True,budget=BUDGET,informed=False):
 rng=np.random.default_rng(seed);v=Oracle();v.budget=budget
 proposals=0;informed_count=0;rejected_bounds=0
 cmin=float(np.linalg.norm(GOAL-START));centre=(START+GOAL)/2;axis=(GOAL-START)/cmin;rotation=np.column_stack((axis,[-axis[1],axis[0]]))
 nodes=[START.copy()];parents=[-1];children=[set()];costs=[0.];events=[];history=[];goal_edges={};best=float('inf');first=None;first_path=None;iteration=0
 def path_to(i):
  out=[];seen=set()
  while i>=0:
   assert i not in seen;seen.add(i);out.append(deg(nodes[i]));i=parents[i]
  return out[::-1]
 def best_goal():
  if not goal_edges:return None,float('inf')
  idx=min(goal_edges,key=lambda j:costs[j]+goal_edges[j]);return idx,costs[idx]+goal_edges[idx]
 def current_path():
  idx,c=best_goal()
  if idx is None:return []
  pp=path_to(idx)
  if np.linalg.norm(nodes[idx]-GOAL)>1e-9:pp.append(deg(GOAL))
  return pp
 def ancestor(a,b):
  # True when a lies on b's parent chain.
  while b>=0:
   if b==a:return True
   b=parents[b]
  return False
 def update_branch(root,newcost):
  oldcost=costs[root];delta=newcost-oldcost;todo=[root];changed=[]
  while todo:
   i=todo.pop();old=costs[i];costs[i]+=delta;changed.append({'node':i,'old_cost_deg':math.degrees(old),'new_cost_deg':math.degrees(costs[i])});todo.extend(sorted(children[i]))
  return changed
 begin=time.perf_counter()
 try:
  while v.calls<budget:
   iteration+=1
   sampling_bound=best
   if informed and math.isfinite(best):
    informed_count+=1
    while True:
     proposals+=1
     theta=rng.uniform(0,math.tau);radius=math.sqrt(rng.random())
     unit=radius*np.array([math.cos(theta),math.sin(theta)])
     radii=np.array([best/2,math.sqrt(max(0,best*best-cmin*cmin))/2])
     sample=centre+rotation@(radii*unit)
     if np.all(np.abs(sample)<=LIMIT):break
     rejected_bounds+=1
   else:
    proposals+=1;sample=rng.uniform(-LIMIT,LIMIT,2)
   arr=np.asarray(nodes);near=int(np.argmin(np.linalg.norm(arr-sample,axis=1)));dd=float(np.linalg.norm(sample-nodes[near]))
   if dd<1e-10:continue
   new=nodes[near]+min(1.,STEP/dd)*(sample-nodes[near]);ok,detail=v.check(nodes[near],new)
   e={'sampling_bound_degrees':None if not math.isfinite(sampling_bound) else math.degrees(sampling_bound),'informed':bool(informed and math.isfinite(sampling_bound)),'iteration':iteration,'sample':deg(sample),'nearest':near,'from':deg(nodes[near]),'to':deg(new),'valid':ok,'steer_validation':detail,'added_index':None,'candidates':[],'rewires':[],'checks_before':v.calls-1}
   if ok:
    distances=np.linalg.norm(arr-new,axis=1);radius=min(math.radians(35),math.radians(720)*(math.log(len(nodes)+1)/(len(nodes)+1))**(1/3))
    nearset=np.flatnonzero(distances<=radius+1e-12).tolist() if star else []
    parent=near;newcost=costs[near]+float(distances[near]);baseline=newcost
    # Cost-ordered parent checks; never choose a shorter-but-colliding edge.
    for j in sorted(nearset,key=lambda j:(costs[j]+distances[j],j)):
     total=costs[j]+float(distances[j])
     if total>=newcost-1e-12:continue
     valid,det=v.check(nodes[j],new);e['candidates'].append({'node':j,'q':deg(nodes[j]),'g_deg':math.degrees(costs[j]),'edge_deg':math.degrees(float(distances[j])),'total_deg':math.degrees(total),'valid':valid,'validation':det})
     if valid:parent=j;newcost=total;break
    idx=len(nodes);nodes.append(new);parents.append(parent);children.append(set());children[parent].add(idx);costs.append(newcost)
    e.update(added_index=idx,parent=parent,nearest_cost_deg=math.degrees(baseline),new_cost_deg=math.degrees(newcost),radius_deg=math.degrees(radius))
    # Rewire only strict improvements; exclude all ancestors, including root.
    if star:
     for j in nearset:
      if j==0 or j==parent or ancestor(j,idx):continue
      proposed=costs[idx]+float(distances[j])
      if proposed>=costs[j]-1e-12:continue
      valid,det=v.check(new,nodes[j])
      if not valid:continue
      oldparent=parents[j];oldcost=costs[j];children[oldparent].remove(j);parents[j]=idx;children[idx].add(j)
      changed=update_branch(j,proposed)
      e['rewires'].append({'node':j,'q':deg(nodes[j]),'old_parent':oldparent,'old_parent_q':deg(nodes[oldparent]),'new_parent':idx,'new_parent_q':deg(new),'old_cost_deg':math.degrees(oldcost),'new_cost_deg':math.degrees(proposed),'affected':changed,'validation':det})
    dist_goal=float(np.linalg.norm(new-GOAL))
    if dist_goal<=STEP+1e-12:
     valid,det=v.check(new,GOAL);e['goal_validation']={'valid':valid,'validation':det}
     if valid:goal_edges[idx]=dist_goal
   e['checks_after']=v.calls;events.append(e)
   j,c=best_goal()
   if c<best-1e-10:
    best=c;h={'checks':v.calls,'iteration':iteration,'cost_degrees':math.degrees(c),'path':current_path()};history.append(h)
    if first is None:first=v.calls;first_path=h['path']
 except Exhausted:
  # The most recent committed tree remains valid. It may contain a partial
  # iteration; record it so playback and metrics never silently diverge.
  if 'e' in locals() and (not events or events[-1] is not e):e['checks_after']=v.calls;e['budget_exhausted']=True;events.append(e)
  j,c=best_goal()
  if c<best-1e-10:history.append({'checks':v.calls,'iteration':iteration,'cost_degrees':math.degrees(c),'path':current_path()})
 elapsed=time.perf_counter()-begin;idx,c=best_goal();path=current_path()
 # Final costs and children are checked against parent chains, not assumed.
 for i in range(len(nodes)):
  assert not ancestor(i,parents[i]);pp=path_to(i);actual=sum(math.dist(a,b) for a,b in zip(pp,pp[1:]));assert abs(actual-math.degrees(costs[i]))<1e-7
  if parents[i]>=0:assert i in children[parents[i]]
 return {'algorithm':'Informed RRT*' if informed else ('RRT*' if star else 'RRT'),'sample_proposals':proposals,'informed_samples':informed_count,'bounds_rejections':rejected_bounds,'seed':seed,'budget':budget,'motion_checks':v.calls,'configuration_checks':v.configurations,'iterations':iteration,'found':bool(path),'first_solution_checks':first,'first_path':first_path,'best_path':path,'best_cost_degrees':None if not path else math.degrees(c),'nodes':[deg(n) for n in nodes],'parents':parents,'costs_degrees':np.degrees(costs).tolist(),'events':events,'history':history,'goal_edges':{str(k):math.degrees(x) for k,x in goal_edges.items()},'runtime_seconds':elapsed,'step_degrees':10,'neighbor_radius_cap_degrees':35,'neighbor_rule':'min(35deg,720deg*(log(n+1)/(n+1))^(1/3)), d=2; teaching geometric model','sampling':'direct uniform informed ellipse after first solution; zero goal bias' if informed else 'uniform full bounded joint space; zero goal bias','metric':'Euclidean radians in bounded two-angle space, no wrap'}

def main():
 A.mkdir(exist_ok=True);Q.mkdir(exist_ok=True)
 runs=[]
 for seed in [1,7,42]:
  for inf in [False,True]:
   r=solve(seed,budget=6000,informed=inf);runs.append(r)
   print({k:r[k] for k in ['algorithm','seed','first_solution_checks','best_cost_degrees','iterations','informed_samples','runtime_seconds']},flush=True)
 main=next(r for r in runs if r['algorithm']=='Informed RRT*' and r['seed']==7)
 for r in runs:
  assert r['motion_checks']==6000
  assert all(b['cost_degrees']<=a['cost_degrees']+1e-8 for a,b in zip(r['history'],r['history'][1:]))
  for h in r['history']:
   for a,b in zip(h['path'],h['path'][1:]):
    qs=np.radians(np.linspace(a,b,1001));cs=clearances(qs);loss=(2*abs(qs[-1,0]-qs[0,0])+abs(qs[-1,1]-qs[0,1]))/1000
    assert cs.min()-loss>0
  for e in r['events']:
   if e['informed']:
    q=np.array(e['sample']);bound=e['sampling_bound_degrees'];lb=np.linalg.norm(q-np.degrees(START))+np.linalg.norm(q-np.degrees(GOAL))
    assert lb<=bound+1e-7
    assert np.max(np.abs(q))<=150+1e-7
 for seed in [1,7,42]:
  a,b=[r for r in runs if r['seed']==seed]
  assert a['first_solution_checks']==b['first_solution_checks']
  assert a['first_path']==b['first_path']
  k=next(i for i,e in enumerate(b['events']) if e['informed'])
  assert all(x['sample']==y['sample'] for x,y in zip(a['events'][:k],b['events'][:k]))
 # Analytical sampler check independent of planning, in degrees.
 rng=np.random.default_rng(20261023);u=rng.random(10000);theta=rng.uniform(0,math.tau,10000)
 pts=np.column_stack([np.sqrt(u)*np.cos(theta)*40,np.sqrt(u)*np.sin(theta)*math.sqrt(700)])
 assert abs(np.mean(np.sum((pts/[40,math.sqrt(700)])**2,axis=1))-.5)<.015
 report={'status':'passed','runs':6,'budget_each':6000,'seeds':[1,7,42],'budget_unit':'whole-edge motion validation calls including extension, parent, rewire, goal; excludes sampler proposals','equal_prefix_until_first_solution':True,'informed_samples_inside_ellipse_and_bounds':True,'parent_chain_costs_verified':True,'acyclic':True,'all_history_paths_densely_verified':True,'best_cost_monotone':True,'uniform_disk_radial_second_moment':float(np.mean(u)),'stats':[{k:r[k] for k in ['algorithm','seed','found','first_solution_checks','motion_checks','best_cost_degrees','iterations','sample_proposals','informed_samples','bounds_rejections']} for r in runs]}
 (A/'informed_run.json').write_text(json.dumps(main,ensure_ascii=False))
 (A/'informed_comparison.json').write_text(json.dumps(runs,ensure_ascii=False))
 (Q/'algorithm_validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
 print('VALIDATED',flush=True)
if __name__=='__main__':main()
