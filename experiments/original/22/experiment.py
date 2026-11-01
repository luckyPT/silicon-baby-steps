"""GCS episode22. Actual Drake GraphOfConvexSets + Clarabel, two-route SOCP.
Each region vertex holds entry/exit points in X_i x X_i; edge continuity
matches exit_u to entry_v. The objective is summed Euclidean segment length.
This is a static 2D point-robot, order-1 special case, not a full arm benchmark.
"""
from pathlib import Path
import json,math,time,importlib.metadata
import numpy as np
from pydrake.geometry.optimization import GraphOfConvexSets,GraphOfConvexSetsOptions,HPolyhedron,CartesianProduct,Point
from pydrake.solvers import ClarabelSolver,L2NormCost,Binding,Cost
B=Path(__file__).parent
START=np.array([0.,0.]);GOAL=np.array([5.,0.])
RECT=np.array([2.2,-.6,2.8,.6])
OBS=np.empty((0,2));RAD=np.empty(0) # legacy shared visual rig compatibility
BOXES={'L':[-.5,-2.,2.,2.],'U':[1.6,1.,3.4,2.],'D':[1.6,-2.,3.4,-1.5],'R':[3.,-2.,5.5,2.]}
BODY_BOXES={'L':[-.5,-2.4,1.6,2.4],'U':[1.4,1.2,3.6,2.4],'D':[1.4,-2.4,3.6,-1.6],'R':[3.4,-2.4,5.5,2.4]}
EDGES=[('S','L'),('L','U'),('U','R'),('L','D'),('D','R'),('R','T')]
def intersects(a,b,rect=RECT):
 a=np.array(a,float);b=np.array(b,float);d=b-a;lo=0.;hi=1.
 for i in range(2):
  if abs(d[i])<1e-12:
   if a[i]<rect[i] or a[i]>rect[i+2]:return False
  else:
   u,v=(rect[i]-a[i])/d[i],(rect[i+2]-a[i])/d[i];lo=max(lo,min(u,v));hi=min(hi,max(u,v))
   if lo>hi:return False
 return True
def length(p):return float(np.linalg.norm(np.diff(np.array(p),axis=0),axis=1).sum())
def build(boxes):
 g=GraphOfConvexSets();vertices={};edges={}
 for k,r in boxes.items():
  x=HPolyhedron.MakeBox(r[:2],r[2:]);v=g.AddVertex(CartesianProduct([x,x]),k);vertices[k]=v
  v.AddCost(Binding[Cost](L2NormCost(np.c_[-np.eye(2),np.eye(2)],np.zeros(2)),v.x()))
 vertices['S']=g.AddVertex(Point(np.r_[START,START]),'S');vertices['T']=g.AddVertex(Point(np.r_[GOAL,GOAL]),'T')
 for a,b in EDGES:
  if a not in vertices or b not in vertices:continue
  e=g.AddEdge(vertices[a],vertices[b]);edges[a+b]=e
  for i in range(2):e.AddConstraint(e.xu()[i+2]==e.xv()[i])
 return g,vertices,edges
def options(solver,seed=1,rounding=0):
 o=GraphOfConvexSetsOptions();o.convex_relaxation=True;o.preprocessing=True;o.max_rounded_paths=rounding;o.rounding_seed=seed;o.solver=solver;o.restriction_solver=solver;o.preprocessing_solver=solver
 return o
def pack(g,v,e,r,boxes,rect=RECT):
 out=dict(success=r.is_success(),status=str(r.get_solution_result()),solver=str(r.get_solver_id().name()))
 if not r.is_success():return out
 out['cost']=float(r.get_optimal_cost());out['flows']={k:float(r.GetSolution(x.phi()))for k,x in e.items()}
 return out
def extract(g,v,e,r,boxes,rect=RECT):
 es=g.GetSolutionPath(v['S'],v['T'],r);names=[es[0].u().name()]+[x.v().name()for x in es];pieces=[];pts=[START.tolist()];continuity=[]
 for k in names:
  z=np.array(v[k].GetSolution(r));pin=z[:2];pout=z[2:];continuity.append(float(np.linalg.norm(pin-np.array(pts[-1]))))
  if k in boxes:
   b=np.array(boxes[k]);assert np.all(pin>=b[:2]-2e-5)and np.all(pin<=b[2:]+2e-5);assert np.all(pout>=b[:2]-2e-5)and np.all(pout<=b[2:]+2e-5)
   assert not intersects(pin,pout,rect),(k,pin,pout)
   pieces.append(dict(region=k,entry=pin.tolist(),exit=pout.tolist()))
  if np.linalg.norm(pin-np.array(pts[-1]))>1e-6:pts.append(pin.tolist())
  if np.linalg.norm(pout-np.array(pts[-1]))>1e-6:pts.append(pout.tolist())
 assert max(continuity)<2e-5 and np.linalg.norm(np.array(pts[-1])-GOAL)<2e-5
 assert all(not intersects(a,b,rect)for a,b in zip(pts,pts[1:]));le=length(pts);assert abs(le-r.get_optimal_cost())<2e-4
 return dict(path=pts,regions=names,pieces=pieces,continuity_residual=max(continuity),length=le,all_segments_analytically_collision_free=True)
def solve(seed=1,boxes=BOXES,rect=RECT,enumerate_paths=True):
 t=time.perf_counter();g,v,e=build(boxes);solver=ClarabelSolver();r=g.SolveShortestPath(v['S'],v['T'],options(solver,seed,0));out=dict(seed=seed,boxes=boxes,edges=list(e),relaxation=pack(g,v,e,r,boxes),elapsed_s=None)
 if not r.is_success():out['elapsed_s']=time.perf_counter()-t;return out
 rr=g.SolveShortestPath(v['S'],v['T'],options(solver,seed,10));out['rounded']=pack(g,v,e,rr,boxes);assert rr.is_success();out['rounded'].update(extract(g,v,e,rr,boxes,rect))
 assert out['relaxation']['cost']<=out['rounded']['cost']+2e-5
 out['relative_bound_gap']=(out['rounded']['cost']-out['relaxation']['cost'])/max(1e-12,out['relaxation']['cost'])
 if enumerate_paths:
  out['restrictions']={}
  for name,keys in [('upper',['SL','LU','UR','RT']),('lower',['SL','LD','DR','RT'])]:
   if not all(k in e for k in keys):continue
   res=g.SolveConvexRestriction([e[k]for k in keys],options(solver));entry=pack(g,v,e,res,boxes)
   if res.is_success():entry.update(extract(g,v,e,res,boxes,rect))
   out['restrictions'][name]=entry
  costs=[r['cost']for r in out['restrictions'].values()if r['success']];assert abs(out['rounded']['cost']-min(costs))<2e-5
 out['elapsed_s']=time.perf_counter()-t;return out
def main():
 for boxes,obstacle in [(BOXES,RECT),(BODY_BOXES,RECT+np.array([-.5,-.5,.5,.5]))]:
  for r in boxes.values():
   assert r[2]<obstacle[0] or r[0]>obstacle[2] or r[3]<obstacle[1] or r[1]>obstacle[3]
  for a,b in EDGES:
   if a in boxes and b in boxes:
    x,y=np.array(boxes[a]),np.array(boxes[b]);assert np.all(np.maximum(x[:2],y[:2])<=np.minimum(x[2:],y[2:]))
 runs=[solve(seed)for seed in [1,7,17]];upper=2*math.sqrt(5)+1;lower=6.
 for r in runs:
  assert abs(r['rounded']['length']-upper)<2e-5
  assert abs(r['restrictions']['lower']['length']-lower)<2e-5
  assert any(1e-3<f<1-1e-3 for f in r['relaxation']['flows'].values())
  assert abs(r['relaxation']['cost']-5)<2e-5
 portals=[[0,0],[1.8,1.5],[3.2,1.5],[5,0]];assert all(not intersects(a,b)for a,b in zip(portals,portals[1:]))
 shorter=[[0,0],[2.18,.62],[2.82,.62],[5,0]];assert all(not intersects(a,b)for a,b in zip(shorter,shorter[1:]));assert length(shorter)<upper
 failure=solve(1,{k:v for k,v in BOXES.items()if k in ['L','R']});assert not failure['relaxation']['success']
 coverage_recovery=solve(1,{k:v for k,v in BOXES.items()if k in ['L','U','R']});assert abs(coverage_recovery['rounded']['length']-upper)<2e-5
 inflated=RECT+np.array([-.5,-.5,.5,.5]);body=solve(1,BODY_BOXES,inflated);assert abs(body['rounded']['length']-5.8)<2e-5
 old_path=runs[0]['rounded']['path'];assert any(intersects(a,b,inflated)for a,b in zip(old_path,old_path[1:]))
 d=dict(episode=22,implementation='Actual Drake GraphOfConvexSets with Clarabel; custom 2D entry/exit region model',drake_version=importlib.metadata.version('drake'),scope='Static point robot, length-only polygonal path; no trajectory timing, dynamics or physical robot',start=START.tolist(),goal=GOAL.tolist(),obstacle=RECT.tolist(),runs=runs,analytic=dict(upper=upper,lower=lower),portal_center_baseline=dict(path=portals,length=length(portals)),outside_cover_feasible=dict(path=shorter,length=length(shorter),margin=.02),coverage_failure=failure,coverage_recovery=coverage_recovery,body_recovery=dict(radius=.5,conservative_inflated_box=inflated.tolist(),old_point_path_fails_inflated_box=True,result=body),claims=['Three seeds vary rounding only; they are not three independent environments','All graph paths enumerated for this two-route DAG; no general enumeration scalability claim','Relaxed result is fractional; not an executable path','Costs and bounds are numerical within tolerances, not exact formal certificates','No runtime ranking against other planners'])
 (B/'qa').mkdir(exist_ok=True);(B/'qa/experiment.json').write_text(json.dumps(d,ensure_ascii=False,indent=2,allow_nan=False))
 for r in runs:print('seed',r['seed'],'LB',r['relaxation']['cost'],'rounded',r['rounded']['cost'],'gap',r['relative_bound_gap'])
 print('upper/lower',upper,lower,'portal',length(portals),'outside-cover',length(shorter),'body',body['rounded']['length']);print('ALL ASSERTIONS PASSED')
if __name__=='__main__':main()
