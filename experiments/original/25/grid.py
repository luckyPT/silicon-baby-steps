"""Shared positive-cost grid, fresh A* and independent Dijkstra utilities.
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
