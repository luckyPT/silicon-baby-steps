"""Educational SCO and GP factor experiments, NOT official TrajOpt/GPMP2.
Static 2D point robot, circle obstacle. SI units. Python 3.12, scipy >=1.16.
"""
from pathlib import Path
import json,numpy as np
from scipy.optimize import minimize,least_squares
from scipy.linalg import solve_triangular
from numpy.polynomial import polynomial as poly
B=Path(__file__).resolve().parent;Q=B/'qa';Q.mkdir(exist_ok=True)
OBS=np.array([[2.5,0.]]);RAD=np.array([.65]);EPS=.15

def segment_info(p):
 ds=[];gs=[]
 for i,(a,b) in enumerate(zip(p[:-1],p[1:])):
  for c,r in zip(OBS,RAD):
   v=b-a;u=np.clip((c-a)@v/max(v@v,1e-12),0,1);z=a+u*v-c;l=np.linalg.norm(z);row=np.zeros_like(p);row[i]=(1-u)*z/max(l,1e-12);row[i+1]=u*z/max(l,1e-12);ds.append(l-r);gs.append(row[1:-1].ravel())
 return np.array(ds),np.array(gs)
def knot_info(p):
 ds=[];gs=[]
 for i,z in enumerate(p):
  for c,r in zip(OBS,RAD):
   v=z-c;l=np.linalg.norm(v);row=np.zeros_like(p);row[i]=v/max(l,1e-12);ds.append(l-r);gs.append(row[1:-1].ravel())
 return np.array(ds),np.array(gs)
def energy(p):return float(np.sum(np.diff(p,axis=0)**2))
def metrics(p):return dict(energy=energy(p),length=float(np.linalg.norm(np.diff(p,axis=0),axis=1).sum()),knot_clearance=float(knot_info(p)[0].min()),segment_clearance=float(segment_info(p)[0].min()))
def sco(initial,mode='segment',budget=60):
 p=initial.copy();ni=(len(p)-2)*2;fun=segment_info if mode=='segment' else knot_info;hist=[dict(iteration=0,path=p.tolist(),**metrics(p))];attempts=[];r=.35
 for mu in [2.,20.,200.]:
  for k in range(budget//3):
   d,G=fun(p);x=p[1:-1].ravel();m=len(d)
   def unpack(z):return np.vstack([p[0],z[:ni].reshape(-1,2),p[-1]])
   def f(z):return energy(unpack(z))+mu*z[ni:].sum()
   def jac(z):
    pp=unpack(z);return np.r_[(2*(2*pp[1:-1]-pp[:-2]-pp[2:])).ravel(),np.full(m,mu)]
   z0=np.r_[x,np.maximum(0,EPS-d)];J=np.c_[G,np.eye(m)]
   res=minimize(f,z0,jac=jac,bounds=[(v-r,v+r) for v in x]+[(0,None)]*m,constraints=[dict(type='ineq',fun=lambda z:d+G@(z[:ni]-x)+z[ni:]-EPS,jac=lambda z:J)],method='SLSQP',options={'ftol':1e-10,'maxiter':180})
   if not res.success:attempts.append(dict(mu=mu,accepted=False,reason=res.message));r*=.5;continue
   trial=unpack(res.x);old=energy(p)+mu*np.maximum(0,EPS-d).sum();new=energy(trial)+mu*np.maximum(0,EPS-fun(trial)[0]).sum();pred=old-f(res.x);gain=old-new;ratio=float(gain/max(pred,1e-12));accept=bool(pred>1e-9 and gain>0 and ratio>.1)
   attempts.append(dict(mu=mu,trust=r,predicted=float(pred),actual=float(gain),ratio=ratio,accepted=accept))
   if accept:
    step=abs(trial-p).max();p=trial;hist.append(dict(iteration=len(hist),mu=mu,path=p.tolist(),**metrics(p)));r=min(.7,r*1.5)if ratio>.75 else r
    if step<1e-5:break
   else:
    if pred<1e-8:break
    r*=.5
   if r<1e-6:break
  if fun(p)[0].min()>=EPS-1e-6:break
 return dict(mode=mode,initial=initial.tolist(),path=p.tolist(),history=hist,attempts=attempts,final=metrics(p))
def hermite_coeff(a,b,dt):
 p,v=a[:2],a[2:];q,w=b[:2],b[2:];return np.array([p,dt*v,-3*p-2*dt*v+3*q-dt*w,2*p+dt*v-2*q+dt*w])
def dense_curve(st,dt,count=25):return np.concatenate([poly.polyval(np.linspace(0,1,count,endpoint=False),hermite_coeff(a,b,dt)).T for a,b in zip(st[:-1],st[1:])]+[st[-1:,:2]])
def curve_clearance(st,dt):
 best=1e9
 for a,b in zip(st[:-1],st[1:]):
  cf=hermite_coeff(a,b,dt)
  for c,r in zip(OBS,RAD):
   cc=cf.copy();cc[0]-=c;ss=poly.polyadd(poly.polymul(cc[:,0],cc[:,0]),poly.polymul(cc[:,1],cc[:,1]));rt=poly.polyroots(poly.polyder(ss));us=[0.,1.]+[float(z.real)for z in rt if abs(z.imag)<1e-7 and 0<z.real<1];best=min(best,min(float(np.linalg.norm(poly.polyval(u,cc))-r)for u in us))
 return best
def gp(height=.25):
 n=9;dt=5/(n-1);t=np.linspace(0,5,n);s=np.column_stack([t,height*np.sin(np.pi*t/5),np.ones(n),height*np.pi/5*np.cos(np.pi*t/5)]);s[0]=[0,0,1,0];s[-1]=[5,0,1,0];initial=s.copy();I=np.eye(2);phi=np.block([[I,dt*I],[np.zeros((2,2)),I]]);cov=np.block([[dt**3/3*I,dt**2/2*I],[dt**2/2*I,dt*I]]);L=np.linalg.cholesky(cov);history=[];sigma=.03
 def unpack(x):return np.vstack([s[0],x.reshape(-1,4),s[-1]])
 def residual(x):
  st=unpack(x);pr=solve_triangular(L,(st[1:]-st[:-1]@phi.T).T,lower=True).T.ravel();pts=dense_curve(st,dt,4);d=np.linalg.norm(pts[:,None,:]-OBS,axis=2)-RAD;return np.r_[pr,np.maximum(0,EPS-d).ravel()/sigma]
 def save(x):
  st=unpack(x);rr=residual(x);history.append(dict(iteration=len(history),states=st.tolist(),path=dense_curve(st,dt).tolist(),cost=float(.5*rr@rr),curve_clearance=float(curve_clearance(st,dt))))
 x0=s[1:-1].ravel();save(x0);res=least_squares(residual,x0,max_nfev=160,ftol=1e-9,xtol=1e-9,gtol=1e-8,callback=lambda x:save(x),method='trf');st=unpack(res.x);save(res.x);exact=curve_clearance(st,dt);sample=float((np.linalg.norm(dense_curve(st,dt,1000)[:,None,:]-OBS,axis=2)-RAD).min());assert abs(exact-sample)<2e-5
 return dict(states=st.tolist(),path=dense_curve(st,dt).tolist(),initial_states=initial.tolist(),history=history,dt=dt,sigma=sigma,cost=float(res.cost),curve_clearance=exact,dense_clearance=sample,nfev=res.nfev,phi=phi.tolist(),Q=cov.tolist())
def main():
 x=np.linspace(0,5,9);p=np.c_[x,.15*np.sin(np.pi*x/5)];xx=np.linspace(0,5,4);coarse=np.c_[xx,.08*np.sin(np.pi*xx/5)]
 d=dict(model='Static planar point robot. Circle obstacle. 3D rendering does not increase planning dimension.',implementation='Educational SCO/GP least squares, not official TrajOpt/GPMP2 performance reproduction',obstacles=OBS.tolist(),radii=RAD.tolist(),epsilon=EPS,sco=sco(p),sco_lower=sco(p*np.array([1,-1])),symmetry=sco(np.c_[x,np.zeros_like(x)]),knot_only=sco(coarse,'knot'),coarse_segment=sco(coarse),gp=gp(),gp_lower=gp(-.25))
 assert d['sco']['final']['segment_clearance']>=EPS-1e-5 and d['coarse_segment']['final']['segment_clearance']>=EPS-1e-5
 assert d['knot_only']['final']['knot_clearance']>EPS and d['knot_only']['final']['segment_clearance']<0 and d['symmetry']['final']['segment_clearance']<0 and d['gp']['curve_clearance']>0
 ds,g=segment_info(p);fd=np.zeros_like(g);h=1e-6
 for j in range(g.shape[1]):
  a=p.copy();b=p.copy();a[1:-1].flat[j]+=h;b[1:-1].flat[j]-=h;fd[:,j]=(segment_info(a)[0]-segment_info(b)[0])/(2*h)
 error=float(abs(fd-g).max());assert error<1e-6;d['gradient_check_max_error']=error
 (Q/'experiment.json').write_text(json.dumps(d,ensure_ascii=False,indent=2));print('SCO',d['sco']['final'],'GP clearance',d['gp']['curve_clearance'],'gradient error',error,flush=True)
if __name__=='__main__':main()
