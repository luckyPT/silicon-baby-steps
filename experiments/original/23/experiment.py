"""Basic LPA* after Koenig et al. AIJ 2004, self-authored implementation.
Fixed endpoints, positive-cost four-neighbor graph, changes between queries.
Actual events, fresh A*, separate reverse-Dijkstra oracle; no physical robot.
"""
from pathlib import Path
import heapq,math,json,random
import numpy as np
B=Path(__file__).parent;INF=math.inf;OBS=np.empty((0,2));RAD=np.empty(0)
W,H=23,15;START=(1,7);GOAL=(21,7)
def finite(x):return None if math.isinf(x)else x
def same(a,b):return a==b or(abs(a-b)<1e-9 if math.isfinite(a)and math.isfinite(b)else False)
class Graph:
 def __init__(self,w=W,h=H,start=START,goal=GOAL,blocked=()):
  self.w=w;self.h=h;self.start=start;self.goal=goal;self.nodes=[(x,y)for y in range(h)for x in range(w)];self.blocked=set(blocked);self.soft={}
  self.adj={u:sorted((x,y)for x,y in [(u[0]-1,u[1]),(u[0]+1,u[1]),(u[0],u[1]-1),(u[0],u[1]+1)]if 0<=x<w and 0<=y<h)for u in self.nodes}
 def c(self,u,v):return INF if u in self.blocked or v in self.blocked else max(self.soft.get(u,1),self.soft.get(v,1))
 def heuristic(self,u):return abs(u[0]-self.goal[0])+abs(u[1]-self.goal[1])
 def update(self,block=(),unblock=(),soft=None):
  touched=set(block)|set(unblock)|set((soft or{}));old={(u,v):self.c(u,v)for u in touched for v in self.adj[u]};old.update({(v,u):self.c(v,u)for u in touched for v in self.adj[u]})
  self.blocked.update(block);self.blocked.difference_update(unblock)
  for u,c in(soft or{}).items():assert c>=1;self.soft[u]=c
  return sorted((u,v,a,self.c(u,v))for(u,v),a in old.items()if not same(a,self.c(u,v)))
 def snapshot(self):return dict(width=self.w,height=self.h,start=self.start,goal=self.goal,blocked=sorted(self.blocked),soft=[dict(cell=k,cost=v)for k,v in sorted(self.soft.items())if v!=1])
def extract(G,dist):
 if math.isinf(dist[G.goal]):return []
 p=[G.goal];seen={G.goal}
 while p[-1]!=G.start:
  v=p[-1];u=min(G.adj[v],key=lambda u:(dist[u]+G.c(u,v),u));assert same(dist[u]+G.c(u,v),dist[v]),('broken chain',u,v)
  assert u not in seen and dist[u]<dist[v];p.append(u);seen.add(u)
 return p[::-1]
def validate_path(G,path,cost):
 if math.isinf(cost):assert path==[];return
 assert path[0]==G.start and path[-1]==G.goal;total=0
 for u,v in zip(path,path[1:]):
  u,v=tuple(u),tuple(v);assert u not in G.blocked and v not in G.blocked;assert abs(u[0]-v[0])+abs(u[1]-v[1])==1;assert v in G.adj[u] and math.isfinite(G.c(u,v));total+=max(G.soft.get(u,1),G.soft.get(v,1))
 assert same(total,cost)
def astar(G):
 g={u:INF for u in G.nodes};g[G.start]=0;q=[(G.heuristic(G.start),0,G.start)];closed=set();events=[];scans=0
 while q:
  f,d,u=heapq.heappop(q)
  if d!=g[u]or u in closed:continue
  closed.add(u);events.append(list(u))
  if u==G.goal:break
  for v in G.adj[u]:
   scans+=1;z=d+G.c(u,v)
   if z<g[v]:g[v]=z;heapq.heappush(q,(z+G.heuristic(v),z,v))
 p=extract(G,g);validate_path(G,p,g[G.goal]);return dict(cost=g[G.goal],path=p,expansions=len(events),neighbor_scans=scans,events=events)
def oracle(G):
 d={G.goal:0};q=[(0,G.goal)]
 while q:
  du,u=heapq.heappop(q)
  if du!=d[u]:continue
  for v in G.adj[u]:
   z=du+G.c(v,u)
   if z<d.get(v,INF):d[v]=z;heapq.heappush(q,(z,v))
 return d.get(G.start,INF)
class LPA:
 def __init__(self,G):
  self.G=G;self.g={u:INF for u in G.nodes};self.rhs=dict(self.g);self.rhs[G.start]=0;self.heap=[];self.live={};self.serial=0;self.reset_stats();self.enqueue(G.start)
 def reset_stats(self):self.events=[];self.updates=0;self.scans=0;self.pushes=0;self.stale=0
 def key(self,u):m=min(self.g[u],self.rhs[u]);return(m+self.G.heuristic(u),m)
 def enqueue(self,u):
  self.live.pop(u,None)
  if self.g[u]!=self.rhs[u]:
   self.serial+=1;k=self.key(u);self.live[u]=(k,self.serial);heapq.heappush(self.heap,(*k,self.serial,u));self.pushes+=1
 def update_vertex(self,u):
  self.updates+=1
  if u!=self.G.start:self.scans+=len(self.G.adj[u]);self.rhs[u]=min(self.g[v]+self.G.c(v,u)for v in self.G.adj[u])
  self.enqueue(u)
 def prune(self):
  while self.heap:
   a,b,serial,u=self.heap[0]
   if self.live.get(u)==((a,b),serial):break
   heapq.heappop(self.heap);self.stale+=1
 def top(self):self.prune();return self.heap[0][:2]if self.heap else(INF,INF)
 def compute(self):
  while self.top()<self.key(self.G.goal)or self.rhs[self.G.goal]!=self.g[self.G.goal]:
   assert self.heap,'Inconsistent goal with empty queue';k1,k2,serial,u=heapq.heappop(self.heap);del self.live[u];before=self.g[u];rhs=self.rhs[u]
   if before>rhs:self.g[u]=rhs;action='accept';targets=self.G.adj[u]
   else:self.g[u]=INF;action='invalidate';targets=[u,*self.G.adj[u]]
   self.events.append(dict(node=u,g_before=finite(before),rhs=finite(rhs),g_after=finite(self.g[u]),action=action,key=[finite(k1),finite(k2)]))
   for v in targets:self.update_vertex(v)
  assert self.g[self.G.goal]==self.rhs[self.G.goal] and not(self.top()<self.key(self.G.goal))
  p=extract(self.G,self.g);validate_path(self.G,p,self.g[self.G.goal]);return dict(cost=self.g[self.G.goal],path=p,expansions=len(self.events),unique_expanded=len(set(tuple(e['node'])for e in self.events)),rhs_updates=self.updates,predecessor_scans=self.scans,queue_pushes=self.pushes,stale_heap_pops=self.stale,events=list(self.events),g_values=[finite(self.g[u])for u in self.G.nodes],rhs_values=[finite(self.rhs[u])for u in self.G.nodes],remaining_inconsistent=sorted(self.live),goal_consistent=True,queue_stop_condition=True)
 def repair(self,changes):
  self.reset_stats()
  for v in sorted(set(v for u,v,a,b in changes)):self.update_vertex(v)
  return self.compute()
def phase(G,L,name,change=None):
 changes=G.update(**change)if change else[];l=L.repair(changes)if change is not None else L.compute();a=astar(G);o=oracle(G);assert same(l['cost'],a['cost'])and same(a['cost'],o)
 return dict(name=name,graph=G.snapshot(),changed_directed_edges=[dict(u=u,v=v,old=finite(c),new=finite(d))for u,v,c,d in changes],lpa=l,astar=a,oracle_cost=o,checks_passed=True)
def main_case():
 blocked={(x,y)for x in range(6,11)for y in range(2,5)}|{(x,y)for x in range(11,16)for y in range(10,13)}
 G=Graph(blocked=blocked);L=LPA(G);ph=[phase(G,L,'initial')]
 ph.append(phase(G,L,'closure',dict(block=[(18,7),(18,6),(18,8)])));assert any(tuple(p)in G.blocked for p in ph[0]['lpa']['path'])
 ph.append(phase(G,L,'reopen',dict(unblock=[(18,7),(18,6),(18,8)])))
 ph.append(phase(G,L,'expensive',dict(soft={(x,7):4 for x in range(16,20)})))
 ph.append(phase(G,L,'cheaper',dict(soft={(x,7):1 for x in range(16,20)})))
 ph.append(phase(G,L,'no_path',dict(block=[(12,y)for y in range(H)])));assert math.isinf(ph[-1]['lpa']['cost'])and ph[-1]['lpa']['path']==[]
 ph.append(phase(G,L,'recovery',dict(unblock=[(12,7)])));assert ph[-1]['lpa']['path']
 ph.append(phase(G,L,'near_start',dict(block=[(2,7),(2,6),(2,8)])))
 return ph
def randomized_tests():
 rows=[]
 for seed in [1,7,17]:
  rng=random.Random(seed);G=Graph(14,10,(0,5),(13,5));L=LPA(G);first=phase(G,L,'initial');assert first['astar']['expansions']==first['lpa']['expansions'];stages=[]
  for k in range(30):
   u=rng.choice([u for u in G.nodes if u not in[G.start,G.goal]]);change=dict(unblock=[u])if u in G.blocked else dict(block=[u]);p=phase(G,L,str(k),change)
   stages.append(dict(change_cell=u,cost=finite(p['lpa']['cost']),lpa_expansions=p['lpa']['expansions'],astar_expansions=p['astar']['expansions'],agrees_with_oracle=True))
  rows.append(dict(seed=seed,independent_map_update_sequence=True,updates=30,stages=stages))
 return rows
def hand_case():return dict(predecessor_g=dict(A=2,B=3),old=dict(gV=3,rhsV=3,consistent=True),cost_increase=dict(gV=3,rhsV=min(2+5,3+2),consistent=False,reset_g_to_infinity_first=True),cost_decrease=dict(gV=5,rhsV=min(2+1,3+2),consistent=False,accept_lower_rhs=True),heuristic_V=4,key_after_increase=[7,3],key_after_decrease=[7,3])
def sanitize(x):
 if isinstance(x,float)and math.isinf(x):return None
 if isinstance(x,dict):return{k:sanitize(v)for k,v in x.items()}
 if isinstance(x,(list,tuple)):return[sanitize(v)for v in x]
 return x
if __name__=='__main__':
 phases=main_case();tests=randomized_tests();out=dict(episode=23,algorithm='Self-authored basic LPA* following AIJ 2004 pseudocode, not official library code',scope='Fixed endpoints, four-neighbor positive-cost graph, stationary queries between map updates; no time-dependent collision or robot execution',width=W,height=H,start=START,goal=GOAL,phases=phases,randomized_tests=tests,hand=hand_case(),metrics='Valid queue-pop expansion events including repeated invalidate/accept. A* includes goal pop. rhs scans, pushes and stale pops separate; map diff, perception, rendering and oracle excluded.',all_assertions='passed')
 (B/'qa').mkdir(exist_ok=True);(B/'qa/experiment.json').write_text(json.dumps(sanitize(out),ensure_ascii=False,indent=2,allow_nan=False))
 for p in phases:print(p['name'],'cost',p['lpa']['cost'],'LPA',p['lpa']['expansions'],'A*',p['astar']['expansions'],'rhs scans',p['lpa']['predecessor_scans'])
 print('90 random update stages + main phases agree with independent oracle. ALL ASSERTIONS PASSED')
