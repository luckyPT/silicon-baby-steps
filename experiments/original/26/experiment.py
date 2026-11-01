"""RRTX core teaching implementation. Positive Euclidean straight local edges.
Based on Otte/Frazzoli IJRR manuscript Algorithms 4,5,8,9,11,12.
Simplifications: retain all original local edges; drain the repair queue;
linear neighbor and changed-edge scans; fixed query endpoints per experiment.
No original/running-neighbor culling, no paper runtime or AO claim for this code.
"""
from pathlib import Path
import numpy as np,math,heapq,json,copy
B=Path(__file__).resolve().parent;Q=B/'qa';Q.mkdir(exist_ok=True)
OBS=np.empty((0,2));RAD=.12
START=[.7,3.];GOAL=[9.3,3.];STATIC=[[4.6,0,5.4,2.05],[4.6,3.95,5.4,6.]]
def hit(a,b,rect,rad=RAD):
 """Slab test against axis-inflated box (conservative square footprint)."""
 lo=np.array(rect[:2])-rad;hi=np.array(rect[2:])+rad;v=np.asarray(b)-a;mn,mx=0.,1.
 for k in range(2):
  if abs(v[k])<1e-13:
   if a[k]<lo[k] or a[k]>hi[k]:return False
  else:
   t=(lo[k]-a[k])/v[k];s=(hi[k]-a[k])/v[k];mn=max(mn,min(t,s));mx=min(mx,max(t,s))
   if mn>mx:return False
 return True
def safe(a,b,boxes):return not any(hit(np.asarray(a),np.asarray(b),o) for o in boxes)
def clean(v):
 if isinstance(v,(np.floating,float)):return float(v) if math.isfinite(v) else None
 if isinstance(v,np.integer):return int(v)
 if isinstance(v,np.ndarray):return clean(v.tolist())
 if isinstance(v,dict):return {str(k):clean(x)for k,x in v.items()}
 if isinstance(v,(tuple,list)):return [clean(x)for x in v]
 return v
class CoreRRTX:
 def __init__(self,seed=7,eps=.03):
  self.rng=np.random.default_rng(seed);self.eps=eps;self.p=[np.array(GOAL)];self.g=[0.];self.lmc=[0.];self.parent=[None];self.children=[set()];self.adj=[set()];self.edges={};self.heap=[];self.active={};self.serial=0;self.boxes=copy.deepcopy(STATIC);self.delta=1.4;self.gamma=480.;self.attempts=0;self.samples=[];self.events=[];self.counters=dict(pops=0,scans=0,rewires=0,edge_checks=0,orphans=0,stale=0)
 def radius(self):
  n=max(2,len(self.p));return min(self.delta,math.sqrt(self.gamma*math.log(n)/(math.pi*n)))
 def key(self,v):return (min(self.g[v],self.lmc[v]),self.g[v])
 def queue(self,v):
  self.serial+=1;self.active[v]=self.serial;heapq.heappush(self.heap,(*self.key(v),self.serial,v))
 def detach(self,v):
  if self.parent[v] is not None:self.children[self.parent[v]].discard(v)
  self.parent[v]=None
 def attach(self,v,u):
  if self.parent[v]!=u:self.detach(v);self.parent[v]=u;self.children[u].add(v);self.counters['rewires']+=1
 def cost(self,v,u):return self.edges[tuple(sorted((v,u)))]['cost']
 def update(self,v):
  if v==0:return
  best=self.lmc[v];target=None
  for u in sorted(self.adj[v]):
   self.counters['scans']+=1
   if self.parent[u]==v:continue
   c=self.cost(v,u)+self.lmc[u]
   if c<best-1e-11:best,target=c,u
  if target is not None:self.lmc[v]=best;self.attach(v,target)
 def rewire(self,v):
  if self.g[v]-self.lmc[v]<=self.eps:return
  for u in sorted(self.adj[v]):
   self.counters['scans']+=1
   if u==self.parent[v]:continue
   c=self.cost(u,v)+self.lmc[v]
   if self.lmc[u]>c+1e-11:
    self.lmc[u]=c;self.attach(u,v)
    if self.g[u]-self.lmc[u]>self.eps:self.queue(u)
 def reduce(self,budget=None):
  n=0
  while self.heap:
   *_,serial,v=heapq.heappop(self.heap)
   if self.active.get(v)!=serial:self.counters['stale']+=1;continue
   if budget is not None and n>=budget:heapq.heappush(self.heap,(*self.key(v),serial,v));break
   del self.active[v];n+=1;self.counters['pops']+=1
   if self.g[v]-self.lmc[v]>self.eps:self.update(v);self.rewire(v)
   self.g[v]=self.lmc[v];self.events.append({'kind':'accept','v':v,'g':self.g[v],'lmc':self.lmc[v],'parent':self.parent[v]})
  return not self.active
 def insert(self,x):
  self.attempts+=1;pts=np.array(self.p);j=int(np.argmin(np.linalg.norm(pts-x,axis=1)));d=np.linalg.norm(x-pts[j]);x=pts[j]+(x-pts[j])*min(1,self.delta/max(d,1e-15))
  if np.min(np.linalg.norm(pts-x,axis=1))<1e-5 or not safe(x,x,self.boxes):return None
  near=list(np.where(np.linalg.norm(pts-x,axis=1)<=self.radius()+1e-10)[0]);links=[]
  for u in near:
   self.counters['edge_checks']+=1
   if safe(x,pts[u],self.boxes):links.append((int(u),float(np.linalg.norm(x-pts[u]))))
  choices=[(d+self.lmc[u],u)for u,d in links if math.isfinite(self.lmc[u])]
  if not choices:return None
  best,u=min(choices);v=len(self.p);self.p.append(x);self.g.append(math.inf);self.lmc.append(best);self.parent.append(None);self.children.append(set());self.adj.append(set());self.attach(v,u)
  for u,d in links:self.adj[v].add(u);self.adj[u].add(v);self.edges[(u,v)]={'base':d,'cost':d}
  self.samples.append(v);self.rewire(v);self.queue(v);self.reduce();return v
 def grow(self,n):
  for _ in range(n):self.insert(self.rng.uniform([.05,.05],[9.95,5.95]))
 def add_query(self):
  v=self.insert(np.array(START));assert v is not None;return v
 def change(self,boxes):
  self.boxes=copy.deepcopy(boxes);changed=[];bad=[];newlyfree=[]
  for (v,u),e in self.edges.items():
   self.counters['edge_checks']+=1;c=e['base'] if safe(self.p[v],self.p[u],boxes)else math.inf
   if c!=e['cost']:
    changed.append([v,u]);old=e['cost'];e['cost']=c
    if c==math.inf:
     if self.parent[v]==u:bad.append(v)
     if self.parent[u]==v:bad.append(u)
    elif old==math.inf:newlyfree.extend([v,u])
  # Obstacle additions: collect the ENTIRE descendant closure before resetting.
  orphan=set(bad);stack=list(bad)
  while stack:
   v=stack.pop()
   for u in self.children[v]:
    if u not in orphan:orphan.add(u);stack.append(u)
  boundary=set()
  for v in orphan:
   boundary.update(self.adj[v]-orphan)
   if self.parent[v] is not None and self.parent[v]not in orphan:boundary.add(self.parent[v])
  for v in orphan:
   self.active.pop(v,None);self.g[v]=self.lmc[v]=math.inf;self.detach(v);self.events.append({'kind':'orphan','v':v})
  self.counters['orphans']+=len(orphan)
  for u in sorted(boundary):
   self.g[u]=math.inf
   self.queue(u)
  for u in sorted(set(newlyfree)):
   self.update(u)
   if self.g[u]!=self.lmc[u]:self.queue(u)
  return {'changed_edges':changed,'orphan_nodes':sorted(orphan),'boundary_nodes':sorted(boundary),'restored_vertices':sorted(set(newlyfree))}
 def path(self,v):
  route=[];seen=set()
  while v is not None:
   if v in seen:return []
   seen.add(v);route.append(v)
   if v==0:return route
   v=self.parent[v]
  return []
 def path_cost(self,route):return sum(self.cost(v,u)for v,u in zip(route,route[1:])) if route else math.inf
 def valid(self,path):return bool(path) and path[-1]==0 and all(safe(self.p[v],self.p[u],self.boxes)for v,u in zip(path,path[1:]))
 def oracle(self,source):
  # Independent forward Dijkstra over the fixed retained graph; re-evaluate geometry.
  dist={source:0.};heap=[(0.,source)];settled=0
  while heap:
   d,v=heapq.heappop(heap)
   if d!=dist[v]:continue
   settled+=1
   if v==0:return d,settled
   for u in self.adj[v]:
    if not safe(self.p[v],self.p[u],self.boxes):continue
    nd=d+float(np.linalg.norm(self.p[v]-self.p[u]))
    if nd<dist.get(u,math.inf):dist[u]=nd;heapq.heappush(heap,(nd,u))
  return math.inf,settled
 def snap(self,name,q,base,changes=None,completed=True):
  path=self.path(q);opt,settled=self.oracle(q);cost=self.path_cost(path);ok=self.valid(path)
  if path:assert ok and cost+1e-8>=opt
  if self.eps==0:assert abs(cost-opt)<1e-7 or cost==opt==math.inf,(name,cost,opt)
  if completed and math.isfinite(opt):assert path
  return clean(dict(name=name,points=self.p,parent=self.parent,g=self.g,lmc=self.lmc,edges=[[v,u]for(v,u),e in self.edges.items()if math.isfinite(e['cost'])],blocked_edges=[[v,u]for(v,u),e in self.edges.items()if not math.isfinite(e['cost'])],boxes=self.boxes,path=path,cost=cost,oracle=opt,oracle_settled=settled,valid=ok,completed=completed,events=self.events[base['event']:],metrics={k:self.counters[k]-base['count'][k]for k in self.counters},nodes=len(self.p),epsilon=self.eps,queue=len(self.active),changes=changes or {}))
 def marker(self):return dict(event=len(self.events),count=self.counters.copy())
def main():
 r=CoreRRTX();ph=[]
 for k,n in [('sample120',120),('sample300',180),('sample650',350)]:
  b=r.marker();r.grow(n)
  # Temporary query node, retained permanently and reused after first insertion.
  if k=='sample120':query=r.add_query()
  ph.append(r.snap(k,query,b))
 old=ph[-1]['path'];cross=next((np.array(r.p[v])+r.p[u])/2 for v,u in zip(old,old[1:])if (r.p[v][0]-5)*(r.p[u][0]-5)<=0)
 cx,cy=cross;box=[4.5,float(cy-.30),5.5,float(cy+.30)]
 b=r.marker();ch=r.change(STATIC+[box]);old_valid=r.valid(old);assert not old_valid
 part=r.reduce(budget=1);partial=r.snap('budget_partial',query,b,ch,part)
 r.reduce();ph.append(r.snap('closure',query,b,ch))
 b=r.marker();ch=r.change(STATIC);r.reduce();ph.append(r.snap('reopen',query,b,ch))
 b=r.marker();ch=r.change(STATIC+[[4.5,1.8,5.5,4.2]]);r.reduce();ph.append(r.snap('no_path',query,b,ch));assert ph[-1]['cost']is None
 b=r.marker();ch=r.change(STATIC);r.reduce();ph.append(r.snap('recovery',query,b,ch))
 b=r.marker();r.grow(350);ph.append(r.snap('sample1000',query,b))
 # Exact zero-threshold configuration vs independent Dijkstra, mixed snapshots.
 checks=[]
 for seed in [1,7,17]:
  t=CoreRRTX(seed,eps=0);t.grow(260);q=t.add_query()
  for i in range(30):
   boxes=STATIC+([]if i%3==0 else [[4.5,1.8,5.5,4.2]]if i%5==0 else [[4.4,1.8+(i%7)*.25,5.6,2.35+(i%7)*.25]])
   b=t.marker();t.change(boxes);t.reduce();ss=t.snap('test',q,b);checks.append(dict(seed=seed,update=i,cost=ss['cost'],oracle=ss['oracle'],valid=ss['valid']))
 results=dict(episode=26,seed=7,query=query,start=START,goal=GOAL,robot_halfwidth=RAD,static_boxes=STATIC,phases=ph,budget_partial=partial,old_path=old,old_path_invalid_after_closure=not old_valid,verification=dict(mixed_updates=len(checks),exact_zero_threshold_passed=True,checks=checks),scope=['RRTX core teaching variant; retain all original local edges; full queue drain; linear scans','2D square halfwidth .12m with conservative axis-inflated boxes; straight holonomic local edges','Original/running neighbor culling and vbot-limited stopping not implemented; no paper complexity or asymptotic proof inherited','Current map snapshots only; no future trajectory prediction, braking dynamics or real robot'])
 (Q/'experiment.json').write_text(json.dumps(results,ensure_ascii=False,indent=2,allow_nan=False))
 summary=[{k:p[k]for k in ['name','nodes','cost','oracle','metrics','queue','epsilon']}for p in ph]
 (Q/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2));print(json.dumps(summary,ensure_ascii=False,indent=2));print('90 exact update checks passed')
if __name__=='__main__':main()
