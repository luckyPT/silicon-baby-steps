"""Episode21 finite-graph mechanism experiments, NOT full AIT*/EIT*/MIT*.
Run: python experiment.py. Units: coordinates/metres; synthetic effort/state checks.
Adaptive heuristic uses full reverse Dijkstra recomputation, not LPA* repair.
"""
from pathlib import Path
import heapq,json,math,time
import numpy as np
from scipy.spatial import cKDTree
B=Path(__file__).parent
OBS=np.array([[2.5,0.]])
RAD=np.array([1.])
START=np.array([0.,0.]);GOAL=np.array([5.,0.])
def free(p):return bool(np.all(np.linalg.norm(OBS-p,axis=1)>RAD+1e-9))
def valid(a,b):
 v=b-a;den=float(v@v)
 t=np.clip((OBS-a)@v/max(den,1e-30),0,1)
 return bool(np.all(np.linalg.norm(OBS-(a+t[:,None]*v),axis=1)>RAD+1e-9))
def samples(seed,n=240,c=None,adaptive=False):
 rng=np.random.default_rng(seed);out=[START,GOAL];attempts=0;gauss=0
 while len(out)<n+2:
  attempts+=1
  if c is None:p=rng.uniform([-.5,-2.5],[5.5,2.5])
  else:
   a=rng.uniform(0,math.tau);r=math.sqrt(rng.random());p=np.array([2.5+c/2*r*math.cos(a),math.sqrt(c*c-25)/2*r*math.sin(a)])
  if not(-.5<=p[0]<=5.5 and -2.5<=p[1]<=2.5):continue
  if free(p):out.append(p);continue
  if adaptive:
   q=p+rng.normal(0,.35,2)
   for x in np.linspace(p,q,21)[1:]:
    if free(x) and -.5<=x[0]<=5.5 and -2.5<=x[1]<=2.5 and (c is None or np.linalg.norm(x-START)+np.linalg.norm(x-GOAL)<c):out.append(x);gauss+=1;break
 return np.array(out),dict(draws=attempts,obstacle_recovered=gauss)
def graph(p,r=1.05):
 adj=[[]for _ in p]
 for a,b in sorted(cKDTree(p).query_pairs(r)):
  d=float(np.linalg.norm(p[a]-p[b]));adj[a].append((b,d));adj[b].append((a,d))
 return adj
def edge(a,b):return tuple(sorted((int(a),int(b))))
def dijkstra(adj,goal,blocked=set()):
 d=[math.inf]*len(adj);d[goal]=0;par={};q=[(0,goal)];visits=0
 while q:
  c,u=heapq.heappop(q)
  if c>d[u]+1e-12:continue
  for v,w in adj[u]:
   visits+=1
   if edge(u,v)in blocked:continue
   if c+w<d[v]-1e-12:d[v]=c+w;par[v]=u;heapq.heappush(q,(c+w,v))
 return np.array(d),par,visits
def pathids(par,goal=1):
 out=[goal]
 while out[-1]!=0:
  if out[-1]not in par:return []
  out.append(par[out[-1]])
 return out[::-1]
def search(p,adj,adaptive):
 cache={};blocked=set();hist=[];checks=0;reverse_visits=0;restarts=0;last=[];t0=time.perf_counter()
 def snapshot(kind,tree,h,active=None,path=[]):
  hist.append(dict(kind=kind,checks=checks,edges=[[a,b]for b,a in tree.items()],invalid=[list(e)for e in sorted(blocked)],reverse_edges=[[u,v]for u,v in h.items()],active=active,path_ids=path,restarts=restarts))
 while True:
  if adaptive:h,rp,vis=dijkstra(adj,1,blocked);reverse_visits+=vis
  else:h=np.linalg.norm(p-GOAL,axis=1);rp={}
  g=[math.inf]*len(p);g[0]=0;par={};q=[(float(h[0]),0.,0)];restart=False
  if not math.isfinite(h[0]):snapshot('disconnected',par,rp);break
  snapshot('reverse' if adaptive else 'start',par,rp)
  while q:
   _,cost,u=heapq.heappop(q)
   if cost>g[u]+1e-12:continue
   if u==1:last=pathids(par);snapshot('solution',par,rp,u,last);break
   for v,w in adj[u]:
    e=edge(u,v)
    if e in blocked or g[u]+w>=g[v]-1e-12:continue
    fresh=e not in cache
    if fresh:cache[e]=valid(p[u],p[v]);checks+=1
    if not cache[e]:
     blocked.add(e)
     if adaptive:
      restarts+=1;snapshot('collision_repair',par,rp,u);restart=True;break
     continue
    g[v]=g[u]+w;par[v]=u;heapq.heappush(q,(g[v]+float(h[v]),g[v],v))
    if fresh and checks%12==0:snapshot('expand',par,rp,u)
   if restart:break
  if restart:continue
  break
 length=float(sum(np.linalg.norm(p[b]-p[a])for a,b in zip(last,last[1:])))if last else None
 if not last:snapshot('failed',par,rp)
 assert not last or all(valid(p[a],p[b])for a,b in zip(last,last[1:]))
 return dict(points=p.tolist(),path_ids=last,path=p[last].tolist(),length=length,checks=checks,invalid_count=len(blocked),reverse_edge_visits=reverse_visits,restarts=restarts,elapsed_s=time.perf_counter()-t0,history=hist)
def run(seed,c=None,n=240):
 p,stats=samples(seed,n,c);adj=graph(p)
 fixed=search(p,adj,False);adapt=search(p,adj,True)
 # Independent exact frozen-graph oracle; its work is excluded from each planner.
 blocked={edge(u,v)for u,a in enumerate(adj)for v,w in a if not valid(p[u],p[v])}
 oracle,_,_=dijkstra(adj,1,blocked)
 # Check heuristic admissibility against the true frozen graph at every repair.
 for h in adapt['history']:
  optimistic,_,_=dijkstra(adj,1,{tuple(e)for e in h['invalid']})
  finite=np.isfinite(oracle)
  assert np.all(optimistic[finite]<=oracle[finite]+1e-8)
 for a in [fixed,adapt]:
  assert (a['length']is None)==(not math.isfinite(oracle[0]))
  if a['length']is not None:assert abs(a['length']-oracle[0])<1e-8
 return dict(seed=seed,sample_count=n,graph_edges=sum(map(len,adj))//2,radius=1.05,sampling=stats,oracle_length=float(oracle[0])if math.isfinite(oracle[0])else None,fixed=fixed,adapt=adapt)
def effort_demo():
 # EIT*-inspired bounded candidate selection ONLY. Actual EIT* uses AEES edge queues.
 routes=[dict(name='A',cost=6.,work_per_edge=[30,30],points=[[0,0],[2.5,1.6],[5,0]]),dict(name='B',cost=7.,work_per_edge=[6,6],points=[[0,0],[2.5,-2.1],[5,0]])]
 for r in routes:
  assert all(valid(np.array(a),np.array(b))for a,b in zip(r['points'],r['points'][1:]))
 lower_bound=min(r['cost']for r in routes);trace=[];cache=set();work=0
 for w in [1.2,1.0]:
  eligible=[r for r in routes if r['cost']<=w*lower_bound+1e-9]
  r=min(eligible,key=lambda r:sum(r['work_per_edge'])if r['name']not in cache else 0)
  before=work
  if r['name']not in cache:
   # A deterministic state-validation workload; work units aren't wall time.
   for i,num in enumerate(r['work_per_edge']):
    a,b=np.array(r['points'][i:i+2]);assert all(free(a+(b-a)*t)for t in np.linspace(0,1,num));work+=num
   cache.add(r['name'])
  trace.append(dict(w=w,limit=w*lower_bound,selected=r['name'],cost=r['cost'],new_state_checks=work-before,total_state_checks=work))
 assert trace[0]['selected']=='B'and trace[1]['selected']=='A'
 return dict(routes=routes,lower_bound=lower_bound,trace=trace,note='Synthetic graph objective costs 6/7, not Euclidean lengths. Effort is discrete state checks. Not full EIT*.')
def main():
 runs=[run(seed)for seed in [1,7,17]]
 failed=run(1,c=5.05,n=320);recovery=run(1,c=6.2,n=320)
 assert failed['adapt']['length']is None and recovery['adapt']['length']is not None
 # Guaranteed separating cut: every path crosses x=2.5, but this ellipse has |y|<1.
 assert math.sqrt(5.05**2-25)/2<1
 p,stats=samples(7,240,6.2,adaptive=True)
 a=np.array([0.,0.]);b=np.array([5.,0.]);tiny_obs=np.array([1.25,0.]);radius=.12
 sparse=[0.,.5,1.];sparse_ok=all(np.linalg.norm(a+(b-a)*t-tiny_obs)>radius for t in sparse)
 dense_ok=all(np.linalg.norm(a+(b-a)*t-tiny_obs)>radius for t in np.linspace(0,1,101))
 assert sparse_ok and not dense_ok
 data=dict(scope='AIT-inspired full reverse recompute on a frozen RGG; effort toy; MIT estimated-set components. Not official planner implementations or benchmark.',runs=runs,ellipse_failure=failed,ellipse_recovery=recovery,adaptive_samples=dict(points=p.tolist(),stats=stats),effort=effort_demo(),sparse_miss=dict(a=a.tolist(),b=b.tolist(),obstacle=tiny_obs.tolist(),radius=radius,sparse_parameters=sparse,sparse_pass=sparse_ok,dense_101_pass=dense_ok),mit_hand=dict(g=2.,edge_lower=1.,h_lower=2.,s=5.,gamma=.4,expansion=math.sqrt(1+.6**2),estimate=5*math.sqrt(1+.6**2)))
 (B/'qa').mkdir(exist_ok=True);(B/'qa/experiment.json').write_text(json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False))
 for r in runs:print(r['seed'],'cost',r['oracle_length'],'fixed/adapt checks',r['fixed']['checks'],r['adapt']['checks'],'reverse visits',r['adapt']['reverse_edge_visits'])
 print('ellipse',failed['adapt']['length'],recovery['adapt']['length'],'effort',data['effort']['trace']);print('ALL ASSERTIONS PASSED')
if __name__=='__main__':main()
