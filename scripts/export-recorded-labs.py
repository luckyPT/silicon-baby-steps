from pathlib import Path
import json
R=Path(__file__).resolve().parents[1]
# Compact normalized replay records, taken from the actual Python output.
def load(i,name='summary'):
 return json.loads((R/f'experiments/original/{i}/qa/{name}.json').read_text())
def view(label,path,metrics,**kw):return dict(label=label,path=path,metrics=metrics,**kw)
def save(i,views,scope):
 d=dict(episode=i,mode='recorded-experiment',scope=scope,views=views)
 (R/'public/experiments').mkdir(exist_ok=True)
 (R/f'public/experiments/{i}.json').write_text(json.dumps(d,ensure_ascii=False,separators=(',',':'),allow_nan=False)+'\n')
scope='本页回放真实实验完成阶段，参数变化请在原始Python代码中重新计算。路线、代价与工作量来自日志；不把帧数当作算法耗时。'
d=load(19,'experiment');v=[]
for key,label in [('knot_only','只查节点：整段仍碰撞'),('coarse_segment','同四节点：改用整段约束'),('sco','SCO：上绕初值'),('sco_lower','SCO：下绕初值'),('symmetry','对称初值：停滞失败'),('gp','GP先验与插值因子'),('gp_lower','GP：下绕初值')]:
 p=d[key];v.append(view(label,p['path'],p.get('final',{'curve_clearance':p.get('curve_clearance'),'cost':p.get('cost')}),circles=[[2.5,0,.65]],bounds=[-.5,-1.7,5.5,1.7],comparison=[]))
save(19,v,scope+' 自写教学SCO/GP因子实验，并非完整官方TrajOpt/GPMP2。')
d=load(20);v=[]
for run in d['runs']:
 for alg in ['fmt','eager','bit']:
  p=run[alg];v.append(view(f'种子{run["seed"]} · {alg}',p.get('path',[]),{k:x for k,x in p.items()if k in ['length','checks','clearance','expanded','success']},circles=[[2.5,0,.8]],bounds=[-.5,-2.5,5.5,2.5]))
save(20,v,scope+' FMT与全验图共享点集和半径；BIT批次的点集、半径不同。等样本数不等于等预算。')
d=load(21);v=[]
for run in d['runs']:
 for alg in ['fixed','adapt']:
  p=run[alg];v.append(view(f'种子{run["seed"]} · {alg}',p['path'],{k:x for k,x in p.items()if k!='path'},circles=[[2.5,0,1]],bounds=[-.5,-2.5,5.5,2.5]))
save(21,v,scope+' 适应版全量重算反向Dijkstra；是AIT*启发的组件变体。少检碰同时增加了反向邻接访问。')
d=load(22);v=[]
for run in d['runs']:
 v.append(view(f'舍入种子{run["seed"]}',run['path'],{k:run[k]for k in ['lower_bound','rounded_length','relative_bound_gap','continuity_residual']},boxes=[[2.2,-.6,2.8,.6]],bounds=[-.5,-2,5.5,2],comparison=d['portal_center_baseline']['path']))
save(22,v,scope+' 同一人工凸区域图，Drake/Clarabel实际求解；虚线是固定交接中心基线。松弛下界不等于可执行路线。')
for i,alg in [(23,'lpa'),(24,'dstar'),(25,'result')]:
 d=load(i,'experiment');v=[]
 for p in d['phases']:
  a=p[alg];g=p['graph'];metrics={k:a[k]for k in ['cost','expansions','predecessor_scans','neighbor_scans','lazy_key_updates','km','epsilon','completed','cumulative_expansions']if k in a}
  metrics['oracle_cost']=p['oracle_cost'];metrics['astar_expansions']=p['astar']['expansions'];v.append(view(p['name'],a['path'],metrics,grid=g,bounds=[-.5,-.5,g['width']-.5,g['height']-.5],comparison=p['astar']['path']))
 save(i,v,scope+' 实线为本算法，虚线为当前图重跑A*；有效扩展与维护工作不能换算为速度倍数。')
d=load(26,'experiment');v=[]
for p in d['phases']+[d['budget_partial']]:
 pts=p['points'];path=[pts[k]for k in p['path']];metrics={k:p[k]for k in ['cost','oracle','nodes','queue','epsilon','completed']};metrics.update(p['metrics'])
 v.append(view(p['name'],path,metrics,points=pts,tree=[[pts[k],pts[u]]for k,u in enumerate(p['parent'])if u is not None],boxes=p['boxes'],robotHalfwidth=.12,bounds=[0,0,10,6]))
save(26,v,scope+' 保留全部邻接的核心教学变体；整图是完成阶段快照，预算阶段是真实中断状态。ε为局部传播阈值。')
print('Exported genuine experiment snapshots for 19–26')
