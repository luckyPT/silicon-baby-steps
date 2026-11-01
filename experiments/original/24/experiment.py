"""Self-authored basic D* Lite, AAAI 2002 Figure 3; integer-cost grid.
Movement occurs between stationary planning calls. No prediction or dynamics.
"""
from pathlib import Path
import heapq,math,json,random,time,statistics
import numpy as np
B=Path(__file__).resolve().parent;INF=math.inf;OBS=np.empty((0,2));RAD=np.empty(0)
W,H=23,15;START=(1,7);GOAL=(21,7)
def h(a,b):return abs(a[0]-b[0])+abs(a[1]-b[1])
def finite(x):return None if math.isinf(x) else x
class Graph:
 def __init__(self,w=W,ht=H,start=START,goal=GOAL,blocked=()):
  self.w=w;self.h=ht;self.start=start;self.goal=goal;self.nodes=[(x,y)for y in range(ht)for x in range(w)];self.blocked=set(blocked);self.soft={}
  self.adj={u:sorted(v for v in [(u[0]-1,u[1]),(u[0]+1,u[1]),(u[0],u[1]-1),(u[0],u[1]+1)]if 0<=v[0]<w and 0<=v[1]<ht)for u in self.nodes}
 def c(self,u,v):return INF if u in self.blocked or v in self.blocked else max(self.soft.get(u,1),self.soft.get(v,1))
 def update(self,block=(),unblock=(),soft=None):
  touched=set(block)|set(unblock)|set(soft or{});edges={(u,v)for u in touched for v in self.adj[u]}|{(v,u)for u in touched for v in self.adj[u]};old={e:self.c(*e)for e in edges}
  self.blocked.update(block);self.blocked.difference_update(unblock)
  for u,c in(soft or{}).items():assert c>=1;self.soft[u]=c
  return [(u,v,a,self.c(u,v))for(u,v),a in sorted(old.items())if a!=self.c(u,v)]
 def snapshot(self):return dict(width=self.w,height=self.h,start=self.start,goal=self.goal,blocked=sorted(self.blocked),soft=[dict(cell=k,cost=v)for k,v in sorted(self.soft.items())if v!=1])
def validate(G,path,cost):
 if math.isinf(cost):assert not path;return
 assert tuple(path[0])==G.start and tuple(path[-1])==G.goal
 assert all(tuple(v)in G.adj[tuple(u)]and tuple(u)not in G.blocked and tuple(v)not in G.blocked for u,v in zip(path,path[1:]))
 assert sum(G.c(tuple(u),tuple(v))for u,v in zip(path,path[1:]))==cost

def astar(G):
 d={G.start:0};prev={};q=[(h(G.start,G.goal),0,G.start)];closed=set();pops=0;scans=0
 while q:
  _,du,u=heapq.heappop(q)
  if du!=d[u]or u in closed:continue
  closed.add(u);pops+=1
  if u==G.goal:break
  for v in G.adj[u]:
   scans+=1;z=du+G.c(u,v)
   if z<d.get(v,INF):d[v]=z;prev[v]=u;heapq.heappush(q,(z+h(v,G.goal),z,v))
 cost=d.get(G.goal,INF);path=[]
 if math.isfinite(cost):
  path=[G.goal]
  while path[-1]!=G.start:path.append(prev[path[-1]])
  path.reverse()
 validate(G,path,cost);return dict(cost=cost,path=path,expansions=pops,neighbor_scans=scans)
def oracle(G):
 # Independent forward Dijkstra, no heuristic, no persistent state.
 q=[(0,G.start)];dist={G.start:0}
 while q:
  du,u=heapq.heappop(q)
  if du!=dist[u]:continue
  if u==G.goal:return du
  for v in G.adj[u]:
   z=du+G.c(u,v)
   if z<dist.get(v,INF):dist[v]=z;heapq.heappush(q,(z,v))
 return INF
class DStarLite:
 def __init__(self,G):
  self.G=G;self.g={u:INF for u in G.nodes};self.rhs=dict(self.g);self.rhs[G.goal]=0;self.last=G.start;self.km=0;self.heap=[];self.live={};self.serial=0;self.reset();self.enqueue(G.goal)
 def reset(self):self.events=[];self.scans=0;self.pushes=0;self.stale=0;self.rekeys=0
 def key(self,u):
  m=min(self.g[u],self.rhs[u]);return(m+h(self.G.start,u)+self.km,m)
 def enqueue(self,u):
  self.live.pop(u,None)
  if self.g[u]!=self.rhs[u]:
   self.serial+=1;k=self.key(u);self.live[u]=(k,self.serial);heapq.heappush(self.heap,(*k,self.serial,u));self.pushes+=1
 def prune(self):
  while self.heap:
   a,b,s,u=self.heap[0]
   if self.live.get(u)==((a,b),s):break
   heapq.heappop(self.heap);self.stale+=1
 def top(self):self.prune();return self.heap[0][:2]if self.heap else(INF,INF)
 def update_vertex(self,u):
  if u!=self.G.goal:self.scans+=len(self.G.adj[u]);self.rhs[u]=min(self.G.c(u,v)+self.g[v]for v in self.G.adj[u])
  self.enqueue(u)
 def compute(self):
  count=0
  while self.top()<self.key(self.G.start)or self.rhs[self.G.start]!=self.g[self.G.start]:
   count+=1;assert count<100000
   a,b,s,u=heapq.heappop(self.heap);del self.live[u];old=(a,b);new=self.key(u)
   if old<new:self.enqueue(u);self.rekeys+=1;continue
   before=self.g[u];rhs=self.rhs[u]
   if before>rhs:self.g[u]=rhs;action='accept';targets=self.G.adj[u]
   else:self.g[u]=INF;action='invalidate';targets=[u,*self.G.adj[u]]
   self.events.append(dict(node=u,action=action,g_before=finite(before),rhs=finite(rhs),g_after=finite(self.g[u])))
   for v in targets:self.update_vertex(v)
  assert self.rhs[self.G.start]==self.g[self.G.start]and self.top()>=self.key(self.G.start)
  cost=self.g[self.G.start];path=[]
  if math.isfinite(cost):
   path=[self.G.start]
   while path[-1]!=self.G.goal:
    u=path[-1];v=min(self.G.adj[u],key=lambda v:(self.G.c(u,v)+self.g[v],v));assert self.G.c(u,v)+self.g[v]==self.g[u]and self.g[v]<self.g[u];path.append(v)
  validate(self.G,path,cost)
  return dict(cost=cost,path=path,expansions=len(self.events),events=list(self.events),successor_scans=self.scans,queue_pushes=self.pushes,stale_heap_pops=self.stale,lazy_key_updates=self.rekeys,g_values=[finite(self.g[u])for u in self.G.nodes],km=self.km,start_consistent=True,queue_stop_condition=True)
 def repair(self,changes=()):
  self.reset();self.km+=h(self.last,self.G.start);self.last=self.G.start
  # Changing directed edge u->v affects rhs(u), not rhs(v).
  for u in sorted(set(u for u,v,a,b in changes)):self.update_vertex(u)
  return self.compute()
def phase(G,D,name,change=None):
 changes=G.update(**change)if change else[];t=time.perf_counter_ns();d=D.repair(changes);dt=(time.perf_counter_ns()-t)/1e6;t=time.perf_counter_ns();a=astar(G);at=(time.perf_counter_ns()-t)/1e6;o=oracle(G);assert d['cost']==a['cost']==o
 return dict(name=name,graph=G.snapshot(),changed_directed_edges=[dict(u=u,v=v,old=finite(c),new=finite(vv))for u,v,c,vv in changes],dstar=d,astar=a,oracle_cost=o,dstar_observed_ms=dt,astar_observed_ms=at,checks_passed=True)
def move_along(G,D,p,n):
 for v in p['dstar']['path'][1:n+1]:assert tuple(v)in G.adj[G.start]and math.isfinite(G.c(G.start,tuple(v)));G.start=tuple(v)
 return phase(G,D,'moved')
def main_case():
 shelves={(x,y)for x in range(6,11)for y in range(2,5)}|{(x,y)for x in range(11,16)for y in range(10,13)}
 G=Graph(blocked=shelves);D=DStarLite(G);ph=[phase(G,D,'initial')]
 p=move_along(G,D,ph[-1],7);p['name']='advance';ph.append(p);assert G.start==(8,7)
 ph.append(phase(G,D,'closure',dict(block=[(10,6),(10,7),(10,8)])))
 old=ph[1]['dstar']['path'];assert any(tuple(v)in G.blocked for v in old)
 p=move_along(G,D,ph[-1],2);p['name']='detour';ph.append(p)
 ph.append(phase(G,D,'reopen',dict(unblock=[(10,6),(10,7),(10,8)])))
 ph.append(phase(G,D,'no_path',dict(block=[(12,y)for y in range(H)])))
 ph.append(phase(G,D,'recovery',dict(unblock=[(12,7)])))
 ph.append(phase(G,D,'soft_up',dict(soft={(x,7):4 for x in range(16,20)})))
 ph.append(phase(G,D,'soft_down',dict(soft={(x,7):1 for x in range(16,20)})))
 return ph

def sensor_case(seed=7,w=23,ht=15):
 rng=random.Random(seed);S=(1,ht//2);T=(w-2,ht//2);truth={(x,y)for x in range(3,w-2)for y in range(ht)if rng.random()<.14};truth|={(9,y)for y in range(3,12)if y<ht};truth.discard(S);truth.discard(T)
 G=Graph(w,ht,S,T);D=DStarLite(G);rows=[];travel=[S]
 for step in range(200):
  visible={v for v in G.nodes if max(abs(v[0]-G.start[0]),abs(v[1]-G.start[1]))<=2};new=(truth&visible)-G.blocked
  p=phase(G,D,f'sense_{step}',dict(block=new));p['newly_seen_blocked']=sorted(new);rows.append(p)
  if G.start==T:break
  if not p['dstar']['path']:break
  v=tuple(p['dstar']['path'][1]);assert v not in truth,'Collision in hidden real map';G.start=v;travel.append(v)
 reached=G.start==T
 return dict(seed=seed,radius_chebyshev=2,sensor_model='Ideal square range, no occlusion, unknown assumed free; static hidden truth',truth=sorted(truth),travel=travel,reached=reached,queries=rows,collision_free=True)
def random_tests():
 out=[]
 for seed in [1,7,17]:
  rng=random.Random(seed);G=Graph(14,10,(0,5),(13,5));D=DStarLite(G);phase(G,D,'init');rows=[]
  for i in range(50):
   cur=D.compute()['path']
   if len(cur)>1 and rng.random()<.7:G.start=tuple(cur[1])
   candidates=[v for v in G.nodes if v not in[G.start,G.goal]];u=rng.choice(candidates)
   if i%5==0:change=dict(soft={u:rng.choice([1,2,5])})
   else:change=dict(unblock=[u])if u in G.blocked else dict(block=[u])
   p=phase(G,D,str(i),change);rows.append(dict(start=G.start,changed=u,cost=finite(p['dstar']['cost']),dstar_expansions=p['dstar']['expansions'],astar_expansions=p['astar']['expansions'],rekeys=p['dstar']['lazy_key_updates'],agrees=True))
  out.append(dict(seed=seed,updates=50,rows=rows))
 return out

def sanitize(x):
 if isinstance(x,float)and math.isinf(x):return None
 if isinstance(x,dict):return{k:sanitize(v)for k,v in x.items()}
 if isinstance(x,(list,tuple)):return[sanitize(v)for v in x]
 return x
if __name__=='__main__':
 ph=main_case();tests=random_tests();nav=sensor_case();assert nav['reached'];out=dict(episode=24,algorithm='Self-authored basic D* Lite after Koenig & Likhachev AAAI 2002 Figure 3',width=W,height=H,start=START,goal=GOAL,phases=ph,randomized_tests=tests,navigation=nav,scope='Stationary planning between discrete grid moves; known graph snapshots, ideal range sensor in separate navigation; no continuous dynamics, prediction, hard real-time or robot execution',all_assertions='passed')
 (B/'qa').mkdir(exist_ok=True);(B/'qa/experiment.json').write_text(json.dumps(sanitize(out),ensure_ascii=False,indent=2,allow_nan=False))
 for p in ph:print(p['name'],p['graph']['start'],'cost',p['dstar']['cost'],'D*',p['dstar']['expansions'],'A*',p['astar']['expansions'],'km',p['dstar']['km'],'rekey',p['dstar']['lazy_key_updates'])
 print('navigation',len(nav['travel'])-1,'steps',len(nav['queries']),'queries; 150 mixed update/move checks PASSED')
