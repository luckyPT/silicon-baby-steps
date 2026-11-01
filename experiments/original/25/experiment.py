"""Self-authored backwards ARA* and basic AD* for fixed-endpoint snapshots.
Primary source: Likhachev et al. ICAPS 2005 Figures 3--5.
Teaching expansion budgets are deterministic, not hard millisecond deadlines.
"""
from pathlib import Path
import heapq,math,json,random,time
from grid import Graph,h,oracle,astar,validate,INF,OBS,RAD,W,H,START,GOAL
B=Path(__file__).resolve().parent
class Queue:
 def __init__(self,key):self.key=key;self.items={};self.heap=[];self.serial=0;self.stale=0;self.pushes=0
 def put(self,u):
  self.serial+=1;k=self.key(u);self.items[u]=(k,self.serial);heapq.heappush(self.heap,(k,self.serial,u));self.pushes+=1
 def remove(self,u):self.items.pop(u,None)
 def prune(self):
  while self.heap:
   k,s,u=self.heap[0]
   if self.items.get(u)==(k,s):break
   heapq.heappop(self.heap);self.stale+=1
 def top(self):self.prune();return self.heap[0][0]if self.heap else(INF,INF)
 def pop(self):self.prune();k,s,u=heapq.heappop(self.heap);del self.items[u];return u
 def rebuild(self,nodes):
  self.items={};self.heap=[]
  for u in sorted(set(nodes)):self.put(u)
def route(G,g):
 if math.isinf(g[G.start]):return [],INF
 p=[G.start];cost=0
 for _ in range(len(G.nodes)):
  if p[-1]==G.goal:validate(G,p,cost);assert cost<=g[G.start]+1e-9;return p,cost
  u=p[-1];v=min(G.adj[u],key=lambda v:(G.c(u,v)+g[v],v));assert math.isfinite(G.c(u,v))and g[v]<g[u],('bad greedy chain',u,v,g[u],g[v]);cost+=G.c(u,v);p.append(v)
 raise AssertionError('cycle')
class ARA:
 def __init__(self,G,eps=3):
  self.G=G;self.eps=eps;self.incumbent_path=[];self.incumbent_cost=INF;self.g={u:INF for u in G.nodes};self.g[G.goal]=0;self.closed=set();self.incons=set();self.Q=Queue(self.key);self.Q.put(G.goal);self.total=0
 def key(self,u):return(self.g[u]+self.eps*h(self.G.start,u),self.g[u])
 def prepare(self,eps):
  assert 1<=eps<=self.eps;self.eps=eps;self.Q.rebuild(set(self.Q.items)|self.incons);self.incons.clear();self.closed.clear()
 def improve(self,limit=None):
  ev=[];done=True
  while self.Q.top()[0]<self.g[self.G.start]:
   if limit is not None and len(ev)>=limit:done=False;break
   u=self.Q.pop();self.closed.add(u);ev.append(dict(node=u,action='accept',g_after=self.g[u]));self.total+=1
   for v in self.G.adj[u]:
    z=self.G.c(v,u)+self.g[u]
    if z<self.g[v]:
     self.g[v]=z
     if v not in self.closed:self.Q.put(v)
     else:self.incons.add(v)
  if done:
   path,cost=route(self.G,self.g)
   if self.incumbent_cost<cost:path,cost=list(self.incumbent_path),self.incumbent_cost
   elif math.isfinite(cost):self.incumbent_path=list(path);self.incumbent_cost=cost
   validate(self.G,path,cost)
  else:path,cost=[],INF
  return dict(epsilon=self.eps,completed=done,has_solution=done and math.isfinite(cost),path=path,cost=cost,stored_start_g=self.g[self.G.start],expansions=len(ev),cumulative_expansions=self.total,events=ev,open_nodes=sorted(self.Q.items),incons_nodes=sorted(self.incons),g_values=[self.g[u]if math.isfinite(self.g[u])else None for u in self.G.nodes],closed_count=len(self.closed))
class AD:
 def __init__(self,G,eps=3):
  self.G=G;self.eps=eps;self.g={u:INF for u in G.nodes};self.rhs=dict(self.g);self.rhs[G.goal]=0;self.closed=set();self.incons=set();self.Q=Queue(self.key);self.Q.put(G.goal);self.total=0
 def key(self,u):
  # Overconsistent nodes are weighted; underconsistent nodes are not.
  if self.g[u]>self.rhs[u]:return(self.rhs[u]+self.eps*h(self.G.start,u),self.rhs[u])
  return(self.g[u]+h(self.G.start,u),self.g[u])
 def update(self,u):
  if u!=self.G.goal:self.rhs[u]=min(self.G.c(u,v)+self.g[v]for v in self.G.adj[u])
  self.Q.remove(u);self.incons.discard(u)
  if self.g[u]!=self.rhs[u]:
   if u not in self.closed:self.Q.put(u)
   else:self.incons.add(u)
 def prepare(self,eps,changes=()):
  assert eps>=1;self.eps=eps
  for u in sorted(set(u for u,v,a,b in changes)):self.update(u)
  self.Q.rebuild(set(self.Q.items)|self.incons);self.incons.clear();self.closed.clear()
 def improve(self,limit=None):
  ev=[];done=True
  while self.Q.top()<self.key(self.G.start)or self.g[self.G.start]!=self.rhs[self.G.start]:
   if limit is not None and len(ev)>=limit:done=False;break
   assert self.Q.items,'empty OPEN with inconsistent start';u=self.Q.pop();before=self.g[u]
   if before>self.rhs[u]:self.g[u]=self.rhs[u];self.closed.add(u);targets=self.G.adj[u];act='accept'
   else:self.g[u]=INF;targets=[u,*self.G.adj[u]];act='invalidate'
   ev.append(dict(node=u,action=act,g_before=before,g_after=self.g[u]));self.total+=1
   for v in targets:self.update(v)
  if done:path,cost=route(self.G,self.g)
  else:path,cost=[],INF
  return dict(epsilon=self.eps,completed=done,has_solution=done and math.isfinite(cost),path=path,cost=cost,stored_start_g=self.g[self.G.start],expansions=len(ev),cumulative_expansions=self.total,events=ev,open_nodes=sorted(self.Q.items),incons_nodes=sorted(self.incons),g_values=[self.g[u]if math.isfinite(self.g[u])else None for u in self.G.nodes],closed_count=len(self.closed))

def check(G,result,eps):
 assert result['completed'];opt=oracle(G);a=astar(G);assert a['cost']==opt
 if math.isfinite(opt):assert result['cost']<=eps*opt+1e-9;assert result['stored_start_g']<=eps*opt+1e-9
 else:assert not result['path'] and math.isinf(result['cost'])
 if eps==1:assert result['cost']==opt
 return opt,a

def make_map(seed):
 r=random.Random(seed);G=Graph();G.blocked={u for u in G.nodes if u not in[G.start,G.goal]and r.random()<.14};G.soft={u:r.choice([2,3,5,7])for u in G.nodes if u not in G.blocked and r.random()<.23};G.blocked.discard(G.start);G.blocked.discard(G.goal);return G

def static_sequence(seed):
 G=make_map(seed);opt=oracle(G)
 if not math.isfinite(opt):return None
 A=ARA(G,3);st=[]
 for eps in [3,2.5,2,1.5,1]:
  if st:A.prepare(eps)
  r=A.improve();o,a=check(G,r,eps);st.append(dict(name='ara_'+str(eps),algorithm='ARA*',graph=G.snapshot(),result=r,oracle_cost=o,astar=a,checks_passed=True))
 return st

def main_case(seed):
 st=static_sequence(seed);G=make_map(seed);D=AD(G,3);ph=list(st)
 def add(name,eps,changes=()):
  if ph and name!='ad_first':D.prepare(eps,changes)
  r=D.improve();o,a=check(G,r,eps);ph.append(dict(name=name,algorithm='AD*',graph=G.snapshot(),result=r,oracle_cost=o,astar=a,changed_edges=len(changes),checks_passed=True));return r
 add('ad_first',3);r=add('ad_optimal',1)
 # Block the midpoint on the previously verified route; endpoints excluded.
 path=r['path'];cell=tuple(path[len(path)//2]);changes=G.update(block=[cell]);r=add('ad_closure',2.5,changes);add('ad_repair_optimal',1)
 changes=G.update(unblock=[cell]);add('ad_reopen',2,changes);add('ad_reopen_optimal',1)
 gate=[tuple(v)for v in ph[-1]['result']['path']if v[0]==12];changes=G.update(block=[(12,y)for y in range(H)]);add('ad_no_path',2,changes)
 changes=G.update(unblock=gate);add('ad_gate',2.5,changes);add('ad_gate_optimal',1)
 return ph,cell

def mixed_tests():
 rows=[]
 for seed in [1,7,17]:
  rng=random.Random(seed);G=Graph(14,10,(0,5),(13,5));D=AD(G,3);check(G,D.improve(),3)
  for i in range(30):
   u=rng.choice([u for u in G.nodes if u not in[G.start,G.goal]])
   change=G.update(soft={u:rng.choice([1,3,5])})if i%5==0 else G.update(**(dict(unblock=[u])if u in G.blocked else dict(block=[u])))
   for eps in [3,2,1]:
    D.prepare(eps,change if eps==3 else());r=D.improve();opt,a=check(G,r,eps);rows.append(dict(seed=seed,update=i,epsilon=eps,cost=r['cost'],optimal=opt,expansions=r['expansions'],bounded=True))
 return rows

def budgets(seed):
 G=make_map(seed);A=ARA(G,3);first=A.improve(limit=5);assert not first['completed']and not first['has_solution'];finish=A.improve();check(G,finish,3);oldpath=finish['path'];oldcost=finish['cost'];A.prepare(1);interrupted=A.improve(limit=1)
 # Old verified incumbent belongs to the unchanged graph, with old completed bound.
 validate(G,oldpath,oldcost);improved=A.improve();check(G,improved,1)
 G2=make_map(seed);D=AD(G2,3);D.improve();D.prepare(1);r=D.improve();cell=tuple(r['path'][len(r['path'])//2]);changes=G2.update(block=[cell]);invalid=any(tuple(v)in G2.blocked for v in r['path']);assert invalid
 D.prepare(2.5,changes);partial=D.improve(limit=1);assert not partial['completed'];resumed=D.improve();check(G2,resumed,2.5)
 return dict(first_budget=5,first=first,finish=finish,improvement_budget=1,improvement_interrupted=interrupted,old_incumbent_valid=True,old_incumbent_cost=oldcost,old_incumbent_bound=3,changed_map_old_path_invalid=invalid,changed_map_partial=partial,improvement_resumed_cost=improved['cost'],repair_resumed_cost=resumed['cost'],changed_map_action='stop; wait for completed and validated repair, no stale bound publication')
def clean(x):
 if isinstance(x,float)and math.isinf(x):return None
 if isinstance(x,dict):return{k:clean(v)for k,v in x.items()}
 if isinstance(x,(tuple,list)):return[clean(v)for v in x]
 return x
if __name__=='__main__':
 chosen=None
 for seed in range(1,100):
  st=static_sequence(seed)
  if st and len(set(p['result']['cost']for p in st))>=3 and any(p['result']['incons_nodes']for p in st):chosen=seed;break
 assert chosen is not None
 ph,cell=main_case(chosen);tests=mixed_tests();budget=budgets(chosen)
 Gk=Graph();K=AD(Gk,2);u=(5,7);K.g[u]=10;K.rhs[u]=6;assert K.key(u)==(14,6);K.g[u]=6;K.rhs[u]=10;assert K.key(u)==(10,6)
 # Independent static ARA* sequences on additional maps, all epsilon stages checked.
 ara_checks=0
 for seed in range(100,120):
  st=static_sequence(seed)
  if st:ara_checks+=len(st)
 out=dict(episode=25,seed=chosen,width=W,height=H,start=START,goal=GOAL,phases=ph,closure_cell=cell,mixed_tests=tests,mixed_updates=90,mixed_queries=len(tests),additional_ara_queries=ara_checks,budgets=budget,all_assertions='passed',scope='Fixed endpoints during each finite graph snapshot; deterministic node expansion caps, no hard-time guarantee, no moving-obstacle prediction or robot execution')
 (B/'qa').mkdir(exist_ok=True);(B/'qa/experiment.json').write_text(json.dumps(clean(out),ensure_ascii=False,indent=2,allow_nan=False))
 for p in ph:print(p['name'],'eps',p['result']['epsilon'],'cost',p['result']['cost'],'opt',p['oracle_cost'],'expand',p['result']['expansions'],'INCONS',len(p['result']['incons_nodes']))
 print('seed',chosen,'closure',cell,'mixed queries',len(tests),'extra ARA',ara_checks,'BUDGET AND ALL ASSERTIONS PASSED')
