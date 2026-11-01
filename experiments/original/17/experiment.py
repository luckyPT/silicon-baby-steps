"""PRM vs edge-lazy PRM, same valid vertices, candidate edges and queries.
Only edges are lazy in this teaching implementation. Original LazyPRM can
also postpone vertex collision tests. Analytic segment/disk checks in 2D.
"""
from pathlib import Path
import numpy as np,json,math,heapq,time
B=Path(__file__).parent;Q=B/'qa';Q.mkdir(exist_ok=True)
OBS=np.array([[1.6,-.65],[2.55,.75],[3.65,-.55]]);RAD=np.array([.45,.5,.45]);LO=np.array([-.4,-2.5]);HI=np.array([5.5,2.5]);N=180;K=10
QUERIES=[([0,-1.7],[5,1.5]),([0,1.7],[5,-1.7]),([0,0],[5,0])]
def clearance(p):return float(np.min(np.linalg.norm(OBS-p,axis=1)-RAD))
def check(a,b):
 d=b-a;u=np.clip(np.sum((OBS-a)*d,axis=1)/max(1e-15,d@d),0,1);rho=np.linalg.norm(OBS-(a+u[:,None]*d),axis=1)-RAD;return bool(np.min(rho)>1e-8)
def key(i,j):return tuple(sorted((int(i),int(j))))
def graph(seed):
 rng=np.random.default_rng(seed);v=[];attempts=0
 while len(v)<N:
  p=rng.uniform(LO,HI);attempts+=1
  if clearance(p)>0:v.append(p)
 v=np.array(v);e=set()
 for i,p in enumerate(v):
  for j in np.argsort(np.linalg.norm(v-p,axis=1))[1:K+1]:e.add(key(i,j))
 return v,sorted(e),attempts

def augment(v,e,a,b):
 vv=np.vstack([v,a,b]);ee=list(e)
 for idx in [N,N+1]:
  for j in np.argsort(np.linalg.norm(v-vv[idx],axis=1))[:K]:ee.append(key(idx,j))
 return vv,sorted(set(ee))

def shortest(v,e,status):
 adj=[[] for _ in v]
 for i,j in e:
  if status.get((i,j)) is False:continue
  w=float(np.linalg.norm(v[i]-v[j]));adj[i].append((j,w));adj[j].append((i,w))
 dist=[math.inf]*len(v);dist[N]=0;par=[-1]*len(v);queue=[(0.,N)];settled=[]
 while queue:
  d,i=heapq.heappop(queue)
  if d>dist[i]+1e-12:continue
  settled.append(i)
  if i==N+1:break
  for j,w in adj[i]:
   nd=d+w
   if nd<dist[j]-1e-12:dist[j]=nd;par[j]=i;heapq.heappush(queue,(nd,j))
 if not math.isfinite(dist[N+1]):return [],None,settled
 path=[];i=N+1
 while i>=0:path.append(i);i=par[i]
 return path[::-1],dist[N+1],settled

def main(seed):
 start=time.perf_counter();v,base,attempts=graph(seed);eagercache={e:check(v[e[0]],v[e[1]]) for e in base};prechecks=len(base);lazycache={};runs=[]
 for qi,(a,b) in enumerate(QUERIES):
  vv,e=augment(v,base,a,b);attach=[x for x in e if max(x)>=N]
  es=dict(eagercache)
  for edge in attach:es[edge]=check(vv[edge[0]],vv[edge[1]])
  ep,ecost,settled=shortest(vv,e,es)
  ls=dict(lazycache);trace=[];checks=0;passes=0
  while True:
   p,cost,_=shortest(vv,e,ls);passes+=1
   if not p:break
   event={'candidate':p,'candidate_cost':cost,'tested':[],'invalid':None}
   for i,j in zip(p,p[1:]):
    edge=key(i,j)
    if edge not in ls:
     valid=check(vv[i],vv[j]);ls[edge]=valid;checks+=1;event['tested'].append({'edge':list(edge),'valid':valid})
     if not valid:event['invalid']=list(edge);break
   trace.append(event)
   if event['invalid'] is None:break
  for edge,valid in ls.items():
   if max(edge)<N:lazycache[edge]=valid
  assert bool(p)==bool(ep)
  if p:
   assert abs(cost-ecost)<1e-8
   assert all(check(vv[i],vv[j]) for i,j in zip(p,p[1:]))
  runs.append({'query':qi+1,'start':a,'goal':b,'vertices':vv.tolist(),'candidate_edges':[list(x) for x in e],'eager_attachment_checks':len(attach),'eager_path':ep,'eager_cost_m':ecost,'eager_search_settled':settled,'lazy_new_edge_checks':checks,'lazy_searches':passes,'lazy_path':p,'lazy_cost_m':cost,'lazy_trace':trace,'all_returned_segments_collision_free':True,'lazy_cache_known_base_edges_after_query':len(lazycache)})
 return {'seed':seed,'sample_attempts':attempts,'valid_base_vertices':N,'k_nearest':K,'base_vertices':v.tolist(),'candidate_base_edges':[list(x) for x in base],'valid_base_edges':[list(x) for x,b in eagercache.items() if b],'eager_base_edge_checks':prechecks,'queries':runs,'eager_total_edge_checks':prechecks+sum(r['eager_attachment_checks'] for r in runs),'lazy_total_edge_checks':sum(r['lazy_new_edge_checks'] for r in runs),'elapsed_s_including_both_planners':time.perf_counter()-start}
if __name__=='__main__':
 out=[main(s) for s in [1,7,17]]
 for r in out:print('SEED',r['seed'],'Eager',r['eager_total_edge_checks'],'Lazy',r['lazy_total_edge_checks'],'searches',[q['lazy_searches'] for q in r['queries']],'cost',[round(q['lazy_cost_m'],3) for q in r['queries']],flush=True)
 d={'model':'Static 2D point robot; three inflated circular obstacles; 3D is visualization only','obstacles':OBS.tolist(),'inflated_radii_m':RAD.tolist(),'bounds':[LO.tolist(),HI.tolist()],'n_valid_vertices':N,'k_nearest':K,'query_count':len(QUERIES),'lazy_variant':'Valid vertices shared with PRM; only candidate edges are checked lazily. Not the full original vertex-lazy formulation.','counting':'Counts segment collision tests, not node tests or graph-search operations. Base caches reused across queries only. Query vertices/attachments removed after each query.','seeds':out}
 (Q/'experiment.json').write_text(json.dumps(d,ensure_ascii=False,indent=2));print('EXPERIMENT COMPLETE')
