"""Training-only decomposition and feature diagnostics (run under flock)."""
import os
os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
os.environ.setdefault('OMP_NUM_THREADS','1')
import sys
sys.dont_write_bytecode=True
import argparse,json
from pathlib import Path
import numpy as np
from fit import load
from metrics import center,corr

HERE=Path(__file__).resolve().parent

def main():
    p=argparse.ArgumentParser();p.add_argument('--mode',default='static');a=p.parse_args()
    d=load(a.mode);m=d['seeds']<500
    y=d['Y'][m].mean(axis=2);labels=d['labels'][m].mean(axis=2)
    dy=center(y)
    for i,n in enumerate(d['label_names']):
        v=labels[:,:,i];dv=center(v)
        print(n,'mean',round(v.mean(),5),'within_sd',round(dv.std(),5),
              'corr(total)',round(corr(dv,dy),4),'covariance share',round(float(np.sum(dv*dy)/np.sum(dy**2)),4))
    X=d['X'][m];names=d['names']
    c=[]
    for i,n in enumerate(names):
        v=center(X[:,:,i])
        if v.std()>1.e-9:c.append((abs(corr(v,dy)),corr(v,dy),n))
    print('Top feature correlations:',sorted(c,reverse=True)[:40])
    # Physically calibrated small formula, learned on training only.
    for ns in [['col','gc','h2_d0'],['col','gc','h2_d0','f_s2_headutility'],
               ['col','gc','f_s2_p1.6_cost'],['col','gc','m_s2_it4_cost']]:
        if not set(ns)<=set(names):continue
        ids=[names.index(n) for n in ns]
        from fit import linear_fit,group_metrics,summarize
        tr=d['seeds']<400;va=(d['seeds']>=400)&(d['seeds']<500)
        xx=d['X'][:,:,ids];yy=d['Y'].mean(axis=2)
        coef,bias=linear_fit(xx[tr],yy[tr],1.)
        pred=xx@coef+bias
        print('Small formula',ns,coef,'intercept',bias)
        print(summarize(' + '.join(ns),group_metrics(pred[va],d['Y'][va],d['tags'])))

if __name__=='__main__':main()
