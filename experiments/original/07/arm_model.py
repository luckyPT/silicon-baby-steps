"""Shared, reproducible 2R geometry; Blender and compositor use the same samples."""
import math,json
from pathlib import Path
import numpy as np
B=Path(__file__).parent;A=B/'assets'
OB=np.array([.9,.5]);RO=.15;RL=.05
def fk(q):
 a,b=np.radians(q);p=np.array([math.cos(a),math.sin(a)])
 return np.array([0.,0.]),p,p+np.array([math.cos(a+b),math.sin(a+b)])
def distance(p,a,b):
 v=b-a;u=np.clip(np.dot(p-a,v)/np.dot(v,v),0,1);n=a+u*v
 return float(np.linalg.norm(p-n)),n
def clearance(q):
 p=fk(q);return min(distance(OB,p[i],p[i+1])[0]-RO-RL for i in range(2))
def interp(a,b,n):return [list(np.array(a)*(1-u)+np.array(b)*u) for u in np.linspace(0,1,n)]
