"""Reproducible geometric FMT* / BIT* teaching experiment (not OMPL benchmark).
Euclidean length, point robot, exact segment-circle collision test, static map.
References and deliberate implementation choices are in README.md.
"""
from pathlib import Path
import json, math, time, heapq
import numpy as np
from scipy.spatial.distance import cdist
B=Path(__file__).parent
OBS=np.array([[2.5,0.]])
RAD=np.array([.8])
START=np.array([0.,0.]);GOAL=np.array([5.,0.])
LOW=np.array([-.5,-2.5]);HIGH=np.array([5.5,2.5]);AREA=float(np.prod(HIGH-LOW))
def clearance(a,b):
    a=np.asarray(a);b=np.asarray(b);v=b-a
    u=np.clip(((OBS-a)@v)/max(float(v@v),1e-20),0,1)
    return float(np.min(np.linalg.norm(a+u[:,None]*v-OBS,axis=1)-RAD))
def free(p):return bool(np.all(np.linalg.norm(OBS-p,axis=1)>RAD))
def samples(n,seed,cbest=math.inf):
    rng=np.random.default_rng(seed);out=[];draws=0
    while len(out)<n:
        p=rng.uniform(LOW,HIGH);draws+=1
        if free(p) and np.linalg.norm(p-START)+np.linalg.norm(p-GOAL)<cbest:out.append(p)
        if draws>2000000:raise RuntimeError('sampling budget')
    return np.array(out),draws
def trace(parent,goal=1):
    if goal not in parent:return []
    out=[goal];seen={goal}
    while out[-1]!=0:
        nxt=parent[out[-1]]
        assert nxt not in seen,'parent cycle'
        seen.add(nxt);out.append(nxt)
    return out[::-1]
def path_metrics(points,ids):
    if not ids:return {'success':False,'length':None,'clearance':None,'path':[]}
    p=points[ids];cl=min(clearance(a,b) for a,b in zip(p,p[1:]));le=float(np.linalg.norm(np.diff(p,axis=0),axis=1).sum());assert cl>0
    return {'success':True,'length':le,'clearance':cl,'path':p.tolist()}
def fmt(points,r,record=True):
    points=np.asarray(points);n=len(points);dist=cdist(points,points);near=[set(np.flatnonzero((dist[i]<r)&(dist[i]>0)))for i in range(n)]
    unvisited=set(range(1,n));opened={0};closed=set();g=np.full(n,np.inf);g[0]=0.;parent={};checks=0;failed=0;events=[];steps=0
    def snap(z):
        if record:events.append({'step':steps,'active':int(z),'open':sorted(opened),'closed':sorted(closed),'edges':[[int(y),int(x)]for x,y in parent.items()],'checks':checks,'best':None if not np.isfinite(g[1]) else float(g[1])})
    snap(0)
    while opened:
        z=min(opened,key=lambda i:(g[i],i))
        if z==1:break
        fresh=set()
        for x in sorted(near[z]&unvisited):
            ys=near[x]&opened
            y=min(ys,key=lambda y:(g[y]+dist[y,x],y))
            checks+=1
            if clearance(points[y],points[x])>0:
                parent[x]=y;g[x]=g[y]+dist[y,x];unvisited.remove(x);fresh.add(x)
            else:failed+=1  # Do not try the second-best parent in this iteration.
        opened.update(fresh);opened.remove(z);closed.add(z);steps+=1
        if steps%4==0:snap(z)
    snap(1 if 1 in opened else 0)
    return dict(algorithm='FMT*',radius=r,n_samples=n-2,points=points.tolist(),history=events,checks=checks,failed_edges=failed,expanded=steps,**path_metrics(points,trace(parent)))
def eager_graph(points,r):
    d=cdist(points,points);adj=[[]for _ in points];checks=0
    for a in range(len(points)):
        for b in range(a+1,len(points)):
            if d[a,b]<r:
                checks+=1
                if clearance(points[a],points[b])>0:adj[a].append((b,d[a,b]));adj[b].append((a,d[a,b]))
    g={0:0.};parent={};q=[(0.,0)]
    while q:
        cost,a=heapq.heappop(q)
        if cost!=g[a]:continue
        if a==1:break
        for b,c in adj[a]:
            if cost+c<g.get(b,math.inf):g[b]=cost+c;parent[b]=a;heapq.heappush(q,(cost+c,b))
    return dict(checks=checks,**path_metrics(points,trace(parent)))
def bit(seed,batches=4,batch_size=80,record=True):
    # Set queues recompute priorities from live tree costs: avoids stale heap keys.
    points=[START.copy(),GOAL.copy()];g={0:0.,1:math.inf};parent={};V={0};X={1};checks=0;expanded=0;rewires=0;events=[];summaries=[];incumbents=[];cbest=math.inf;iteration=0;cache={}
    def h(i):return float(np.linalg.norm(points[i]-GOAL))
    def gh(i):return float(np.linalg.norm(points[i]-START))
    def distance(a,b):return float(np.linalg.norm(points[a]-points[b]))
    def snap(batch):
        if record:events.append({'batch':batch,'step':iteration,'edges':[[int(y),int(x)]for x,y in parent.items()],'vertices':sorted(V),'checks':checks,'best':None if not math.isfinite(g[1]) else g[1],'path_ids':trace(parent)})
    for batch in range(1,batches+1):
        if math.isfinite(cbest):
            X={x for x in X if gh(x)+h(x)<cbest}
            bad={v for v in V if gh(v)+h(v)>cbest+1e-10};V-=bad
            parent={x:y for x,y in parent.items() if x in V and y in V}
            # Retained descendants with disconnected ancestors become samples again.
            connected={0};changed=True
            while changed:
                old=len(connected);connected|={x for x,y in parent.items() if y in connected};changed=len(connected)!=old
            orphan=V-connected;X|=orphan;V=connected
            parent={x:y for x,y in parent.items() if x in V};g={i:(g.get(i,math.inf) if i in V else math.inf)for i in range(len(points))}
        new,draws=samples(batch_size,seed+1000*batch,cbest);base=len(points);points.extend(new);X.update(range(base,len(points)))
        for i in range(base,len(points)):g[i]=math.inf
        oldV=V.copy();QV=V.copy();QE=set();n=len(V|X)
        # Domain volume upper bound instead of exact informed-set volume: conservative larger radius.
        r=2*1.1*math.sqrt(1.5*AREA/math.pi*math.log(n)/n)
        snap(batch)
        while QV or QE:
            def ek(e):a,b=e;return(g[a]+distance(a,b)+h(b),g[a],a,b)
            while QV:
                v=min(QV,key=lambda v:(g[v]+h(v),g[v],v))
                if QE and g[v]+h(v)>ek(min(QE,key=ek))[0]+1e-12:break
                QV.remove(v);expanded+=1
                for x in sorted(X):
                    d=distance(v,x)
                    if d<=r and gh(v)+d+h(x)<cbest:QE.add((v,x))
                if v not in oldV:
                    for x in sorted(V-{v,0}):
                        d=distance(v,x)
                        if d<=r and parent.get(x)!=v and gh(v)+d+h(x)<cbest and g[v]+d<g[x]-1e-12:QE.add((v,x))
            if not QE:continue
            a,b=min(QE,key=ek);QE.remove((a,b));d=distance(a,b);iteration+=1
            if g[a]+d+h(b)>=cbest-1e-12:QV.clear();QE.clear();break
            if g[a]+d>=g.get(b,math.inf)-1e-12:continue
            key=tuple(sorted((a,b)))
            if key not in cache:cache[key]=clearance(points[a],points[b])>0;checks+=1
            if not cache[key]:continue
            if gh(a)+d+h(b)>=cbest-1e-12:continue
            was=b in V;oldg=g.get(b,math.inf);g[b]=g[a]+d;parent[b]=a
            if not was:X.discard(b);V.add(b);QV.add(b)
            else:
                rewires+=1;delta=oldg-g[b];desc=[b]
                while desc:
                    cur=desc.pop()
                    for child,par in list(parent.items()):
                        if par==cur:g[child]-=delta;desc.append(child)
            if g[1]<cbest:
                cbest=g[1];incumbents.append({'batch':batch,'checks':checks,'length':cbest});snap(batch)
            if iteration%12==0:snap(batch)
        cbest=min(cbest,g[1]);snap(batch)
        summaries.append({'batch':batch,'samples_added':batch_size,'total_samples_generated':batch*batch_size,'active_states':len(V|X),'radius':r,'sampling_draws':draws,'checks_cumulative':checks,'best':None if not math.isfinite(cbest)else cbest})
    p=np.array(points);return dict(algorithm='BIT*',seed=seed,points=p.tolist(),history=events,batches=summaries,incumbents=incumbents,checks=checks,expanded=expanded,rewires=rewires,**path_metrics(p,trace(parent)))
def main():
    B.joinpath('qa').mkdir(exist_ok=True);results=[]
    for seed in [1,7,17]:
        p,_=samples(320,seed);p=np.vstack([START,GOAL,p]);f=fmt(p,.95);e=eager_graph(p,.95);bt=bit(seed)
        assert not f['success'] or not e['success'] or f['length']>=e['length']-1e-8
        assert all(a['length']>=b['length']-1e-10 for a,b in zip(bt['incumbents'],bt['incumbents'][1:]))
        results.append({'seed':seed,'fmt':f,'eager':e,'bit':bt})
        print(seed,'FMT',f['success'],f['length'],f['checks'],'eager',e['checks'],'BIT',bt['length'],bt['checks'],flush=True)
    sparsep,_=samples(25,7);sparse=fmt(np.vstack([START,GOAL,sparsep]),.45)
    assert not sparse['success']
    # Geometric checking regression: endpoints outside, segment crosses center.
    assert free(START)and free(GOAL)and clearance(START,GOAL)<0
    plain=np.array([[0.,0.],[1.,0.],[.5,.2],[.5,-.3]])
    # Same algorithm with obstacle-free set: use points far from obstacle.
    f=fmt(plain,1.1,False);e=eager_graph(plain,1.1);assert abs(f['length']-e['length'])<1e-10
    out={'conditions':{'seeds':[1,7,17],'fmt_uniform_samples':320,'fmt_radius':.95,'bit_batches':4,'bit_batch_size':80,'domain':[LOW.tolist(),HIGH.tolist()],'obstacles':OBS.tolist(),'radii':RAD.tolist(),'collision':'exact segment-circle','budget':'equal sample count only; not equal computation budget','bit_choice':'r-disc, rejection informed sampling, domain volume upper bound radius, set-based live queues'},'runs':results,'sparse_failure':sparse,'hand':{'fmt_parent_A':3.5,'fmt_parent_B':3.2,'edge_key_A':5.3,'edge_key_B':5.6,'ellipse_cbest':6.,'ellipse_cmin':5.,'ellipse_a':3.,'ellipse_b':math.sqrt(11)/2},'tests':'segment crossing, FMT obstacle-free graph equality, FMT >= eager graph, BIT monotone incumbents, returned paths exact-clearance passed'}
    (B/'qa/experiment.json').write_text(json.dumps(out,ensure_ascii=False,indent=2,allow_nan=False,default=lambda x:int(x) if isinstance(x,np.integer) else float(x)))
if __name__=='__main__':main()
