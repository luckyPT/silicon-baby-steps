"""Single robot Space-time A*: finite grid, supplied linear obstacle tracks."""
from pathlib import Path
from dataclasses import dataclass
import heapq,itertools,json,math,random,time
OBS=[];RAD=.2;B=Path(__file__).resolve().parent
MOVES=[(1,0),(0,1),(-1,0),(0,-1),(0,0)]
@dataclass
class World:
 name:str; width:int; height:int; start:tuple; goal:tuple; horizon:int; blocked:set; obstacles:list; radius:float=.2
 def free(self,p):return 0<=p[0]<self.width and 0<=p[1]<self.height and tuple(p[:2])not in self.blocked
 def point(self,j,t):return at(self.obstacles[j],t)
def at(tr,t):
 i=min(int(t),len(tr)-1);a=tr[i];b=tr[min(i+1,len(tr)-1)];u=t-int(t)
 return[a[k]+u*(b[k]-a[k])for k in range(2)]
def clearance(a,b,o,q):
 r=[a[k]-o[k]for k in range(2)];v=[b[k]-a[k]-q[k]+o[k]for k in range(2)];vv=sum(x*x for x in v);u=max(0.,min(1.,-sum(r[k]*v[k]for k in range(2))/vv))if vv else 0
 return math.hypot(*(r[k]+u*v[k]for k in range(2)))
def valid(w,a,b,t,mode='continuous'):
 if not(w.free(a)and w.free(b)):return False
 for j in range(len(w.obstacles)):
  o=w.point(j,t);q=w.point(j,t+1)
  if mode=='ignore':continue
  d=min(math.dist(a[:2],o),math.dist(b[:2],q))if mode=='endpoint'else clearance(a,b,o,q)
  if d<=2*w.radius+1e-9:return False
 return True
def hold(w,p,t,mode='continuous'):return all(valid(w,p,p,k,mode)for k in range(t,w.horizon))
def astar(w,mode='continuous'):
 begin=time.perf_counter();serial=itertools.count();h=lambda p:abs(p[0]-w.goal[0])+abs(p[1]-w.goal[1]);s=(*w.start,0);heap=[(h(s),h(s),next(serial),s)];seen={s};parent={};events=[];checks=0;maxopen=1;result=None
 if any(math.dist(w.start,w.point(j,0))<=2*w.radius+1e-9 for j in range(len(w.obstacles))):heap=[]
 while heap:
  _,_,_,s=heapq.heappop(heap);x,y,t=s;events.append(s)
  if (x,y)==w.goal and hold(w,(x,y),t,mode):result=s;break
  if t>=w.horizon:continue
  for dx,dy in MOVES:
   b=(x+dx,y+dy);checks+=1
   if not valid(w,(x,y),b,t,mode):continue
   z=(*b,t+1)
   if z in seen:continue
   seen.add(z);parent[z]=s;heapq.heappush(heap,(t+1+h(z),h(z),next(serial),z))
  maxopen=max(maxopen,len(heap))
 path=[]
 if result:
  z=result
  while True:
   path.append(list(z))
   if z==(*w.start,0):break
   z=parent[z]
  path.reverse()
 return dict(path=path,cost=path[-1][2]if path else None,expanded=len(events),events=events,transition_checks=checks,max_open=maxopen,elapsed_ms=1000*(time.perf_counter()-begin))
# Independent test: quadratic roots rather than projected nearest point.
def oracle_edge(w,a,b,t):
 if not(w.free(a)and w.free(b)):return False
 for j in range(len(w.obstacles)):
  o=w.point(j,t);q=w.point(j,t+1);r=[a[k]-o[k]for k in range(2)];v=[b[k]-a[k]-q[k]+o[k]for k in range(2)];aa=sum(x*x for x in v);bb=2*sum(r[k]*v[k]for k in range(2));cc=sum(x*x for x in r)-(2*w.radius)**2
  if cc<=1e-9:return False
  if aa<1e-16:continue
  d=bb*bb-4*aa*cc
  if d>=0 and max(0,(-bb-math.sqrt(d))/(2*aa))<=min(1,(-bb+math.sqrt(d))/(2*aa))+1e-9:return False
 return True
def oracle(w):
 if any(math.dist(w.start,w.point(j,0))<=2*w.radius+1e-9 for j in range(len(w.obstacles))):return None
 layer={w.start}
 for t in range(w.horizon+1):
  if w.goal in layer and all(oracle_edge(w,w.goal,w.goal,k)for k in range(t,w.horizon)):return t
  layer={b for a in layer for b in [(a[0]+dx,a[1]+dy)for dx,dy in MOVES]if t<w.horizon and oracle_edge(w,a,b,t)}
 return None
def audit(w,p):
 if not p:return dict(feasible=False,waits=None,moves=None,min_separation=None)
 assert tuple(p[0][:2])==w.start and tuple(p[-1][:2])==w.goal
 good=True;waits=0;sep=math.inf
 for a,b in zip(p,p[1:]):
  assert b[2]==a[2]+1 and abs(a[0]-b[0])+abs(a[1]-b[1])<=1
  good &= oracle_edge(w,a,b,a[2]);waits+=a[:2]==b[:2]
  for j in range(len(w.obstacles)):sep=min(sep,clearance(a,b,w.point(j,a[2]),w.point(j,b[2])))
 for t in range(p[-1][2],w.horizon):
  good &= oracle_edge(w,w.goal,w.goal,t)
  for j in range(len(w.obstacles)):sep=min(sep,clearance(w.goal,w.goal,w.point(j,t),w.point(j,t+1)))
 return dict(feasible=bool(good),waits=waits,moves=len(p)-1-waits,min_separation=sep if math.isfinite(sep)else None)
def cases():
 wall={(x,y)for x in range(11)for y in range(5)if y!=2};gate=[[(5,2+min(max(t-6,0),3))for t in range(17)]];allow={(x,2)for x in range(11)}|{(x,1)for x in range(3,8)}
 return[World('crossing',11,7,(1,3),(9,3),16,set(),[[(5,min(t-1,8))for t in range(17)]]),World('gate_wait',11,5,(1,2),(9,2),16,wall,gate),World('meeting',11,5,(1,2),(9,2),16,{(x,y)for x in range(11)for y in range(5)}-allow,[[(max(0,9-t),2)for t in range(17)]]),World('edge_swap',2,1,(0,0),(1,0),1,set(),[[(1,0),(0,0)]]),World('short_horizon',11,5,(1,2),(9,2),10,wall,gate),World('forecast_revision',11,7,(1,3),(9,3),16,set(),[[(5,min(t-2,8))for t in range(17)]])]
def main():
 phases=[]
 for w in cases():
  a=astar(w);o=oracle(w);au=audit(w,a['path']);assert a['cost']==o and(not a['path']or au['feasible']);base=astar(w,'ignore');ep=astar(w,'endpoint')
  p={k:getattr(w,k)for k in ['name','width','height','start','goal','horizon','obstacles','radius']};p.update(blocked=sorted(w.blocked),result=a,oracle=o,audit=au,static_baseline=base,baseline_audit=audit(w,base['path']),endpoint_baseline=ep,endpoint_audit=audit(w,ep['path']));phases.append(p);print(w.name,a['cost'],au,'expanded',a['expanded'])
 mid=World('mid',2,1,(0,0),(1,0),1,set(),[[(.5,-1),(.5,1)]]);assert valid(mid,(0,0),(1,0),0,'endpoint')and not valid(mid,(0,0),(1,0),0)
 dw=World('dwell',3,2,(0,0),(1,0),4,set(),[[(1,2),(1,2),(1,0),(1,2),(1,2)]]);assert astar(dw)['cost']==oracle(dw)==3 and not hold(dw,(1,0),1)
 oldaudit=audit(cases()[-1],phases[0]['result']['path']);assert not oldaudit['feasible']
 rng=random.Random(2705);checks=[]
 for i in range(120):
  w=World('random',7,5,(0,2),(6,2),rng.choice([7,9,12,16]),{(x,y)for x in range(1,6)for y in range(5)if rng.random()<.14},[])
  for j in range(rng.randint(1,3)):
   p=(rng.randrange(1,6),rng.randrange(5));tr=[p]
   for t in range(w.horizon):p=rng.choice([(p[0]+dx,p[1]+dy)for dx,dy in MOVES if 0<=p[0]+dx<7 and 0<=p[1]+dy<5]);tr.append(p)
   w.obstacles.append(tr)
  a=astar(w);o=oracle(w);assert a['cost']==o,(i,a['cost'],o)
  if a['path']:assert audit(w,a['path'])['feasible']
  checks.append(dict(i=i,horizon=w.horizon,cost=o))
 data=dict(episode=27,phases=phases,goal_fixture=dict(early_hold_safe=False,result=astar(dw),oracle=3),forecast_old_plan_audit=oldaudit,validation=dict(random_seed=2705,queries=120,all_passed=True,oracle='Independent time-layer DP, unit-cost Dijkstra equivalent; quadratic-root collision'),random_checks=checks,scope=dict(model='2D position + integer time, 1m/1s axial moves or wait. Robot and obstacle disc radius .2m; contact is collision.',prediction='Given piecewise-linear tracks, held after last endpoint.',goal='Hold at goal until finite horizon, each segment checked.',limits='Earliest arrival on this finite time-expanded graph only. No dynamics, learned prediction, uncertainty, hard realtime, multi-agent negotiation or real robot.'))
 (B/'qa').mkdir(exist_ok=True);(B/'qa/experiment.json').write_text(json.dumps(data,ensure_ascii=False,indent=2));print('120 independent finite-graph queries passed')
if __name__=='__main__':main()
