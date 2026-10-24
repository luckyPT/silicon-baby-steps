"""Reproducible plots from archived geometry and original Python time laws."""
from pathlib import Path
import json,importlib.util
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=Path(__file__).resolve().parents[1];E=R/'experiments/original'
plt.rcParams.update({'figure.facecolor':'#102029','axes.facecolor':'#172f39','text.color':'#dcebee','axes.labelcolor':'#dcebee','xtick.color':'#b7ced4','ytick.color':'#b7ced4','axes.edgecolor':'#77939b','font.size':10})
def save(n,f):f.tight_layout();f.savefig(R/f'public/media/{n}/figure.png',dpi=140);plt.close(f)
v=json.loads((E/'10/qa/algorithm_validation.json').read_text())['stats'];f,ax=plt.subplots(1,2,figsize=(12,4))
for b,c in [(80,'#ffb766'),(70,'#6cdddc')]:
 t=np.linspace(0,2*np.pi,500);ax[0].plot(np.sqrt(b*b-3600)/2*np.sin(t),120+b/2*np.cos(t),color=c,label=f'best {b} deg')
ax[0].scatter([0,0],[90,150],c='white');ax[0].set(xlabel='Relative joint 1 / deg',ylabel='Joint 2 / deg',title='Euclidean proposal regions (not collision-free)');ax[0].legend()
x=np.arange(3);ax[1].bar(x-.18,[v[i]['best_cost_degrees'] for i in [0,2,4]],.36,color='#ffb766',label='RRT*');ax[1].bar(x+.18,[v[i]['best_cost_degrees'] for i in [1,3,5]],.36,color='#6cdddc',label='Informed RRT*');ax[1].set(xticks=x,xticklabels=['Seed 1','Seed 7','Seed 42'],ylabel='Length / deg',title='6000 whole-edge validations each');ax[1].legend();save(10,f)
v=json.loads((E/'11/qa/postprocess_validation.json').read_text());f,ax=plt.subplots(1,2,figsize=(12,4));cols=['#6cdddc','#bbf2a5','#f18888','#ffb766','#a4a1f4']
for(name,parts),col in zip(v['paths'].items(),cols):
 for i,p in enumerate(parts):
  z=np.array(p['controls_deg']);u=np.linspace(0,1,300)[:,None];q=(1-u)*z[0]+u*z[1] if p['kind']=='line' else (1-u)**2*z[0]+2*u*(1-u)*z[1]+u*u*z[2];ax[0].plot(q[:,0],q[:,1],color=col,label=name if i==0 else None)
ax[0].set(xlabel='Joint 1 / deg',ylabel='Joint 2 / deg');ax[0].legend(fontsize=7)
ax[1].bar(['Raw','Shortcut','Blend .5','Blend .25','Direct'],[m['model_clearance_lower_bound_m']*1000 for m in v['metrics'].values()],color=cols);ax[1].axhline(10,color='white',ls='--',label='10mm teaching margin');ax[1].set(ylabel='Clearance lower bound / mm');ax[1].legend();save(11,f)
p=E/'14/motion.py';sp=importlib.util.spec_from_file_location('motion14',p);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);t=np.linspace(0,7,1401);s,v,a,j=m.s_curve(t);ss,vv,aa=m.trapezoid(t)
f,ax=plt.subplots(2,1,figsize=(11,6));ax[0].plot(t,np.where(t<6,1/6,0),label='Uniform: ideal start/stop jumps',color='#a4a1f4');ax[0].plot(t,vv,label='Full path: trapezoid',color='#6cdddc');short=np.linspace(0,np.sqrt(8),600);ax[0].plot(short,.125*np.minimum(short,np.sqrt(8)-short),label='D=.25: different endpoint',color='#ffb766');ax[0].set(ylabel='Progress speed / 1/s');ax[0].legend();ax[1].plot(t,aa,color='#6cdddc');ax[1].set(xlabel='Time / s',ylabel='Progress acceleration / 1/s^2');save(12,f)
f,ax=plt.subplots(3,1,figsize=(11,8))
for i,(xx,yy,unit) in enumerate([(vv,v,'Speed / 1/s'),(aa,a,'Acceleration / 1/s^2'),(np.full_like(t,np.nan),j,'Jerk / 1/s^3')]):
 ax[i].plot(t,xx,color='#ffb766',label='6s trapezoid');ax[i].plot(t,yy,color='#6cdddc',label='7s S-curve');ax[i].set(ylabel=unit)
ax[0].legend();ax[2].set(xlabel='Time / s',title='Trapezoid jerk undefined at jumps; S jerk piecewise constant');save(13,f)
f,ax=plt.subplots(2,2,figsize=(12,7));t=np.linspace(0,10.5,2501)
for k,col in [(1,'#ffb766'),(1.5,'#6cdddc')]:
 q,vel,acc,*_=m.joint_state(t,k)
 for i in range(2):
  for row,(values,limit,unit) in enumerate([(vel,12,'deg/s'),(acc,20,'deg/s^2')]):ax[row,i].plot(t,values[:,i],color=col,label=f'k={k}');ax[row,i].set(ylabel=f'Joint {i+1} / {unit}',xlabel='Common time / s')
for row in range(2):
 for i in range(2):
  for sign in [-1,1]:ax[row,i].axhline(sign*[12,20][row],color='#f18888',ls='--')
  ax[row,i].legend()
f.suptitle('Teaching amplitude limits; acceleration joins still discontinuous');save(14,f)
