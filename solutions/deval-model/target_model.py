"""Learn conditional per-target moves, then calibrate aggregates within each case.

This experiment uses target labels only as responses. Two seed-disjoint training
folds produce out-of-fold component predictions for the design-level calibrator.
The request planner is never run. Run under flock with OMP_NUM_THREADS set.
"""
import os
os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
os.environ.setdefault('OMP_NUM_THREADS','8')
import sys
sys.dont_write_bytecode=True
import argparse
from pathlib import Path
import json
import numpy as np
from sklearn.ensemble import HistGradientBoostingRegressor
import joblib
from fit import load,linear_fit,group_metrics,summarize

HERE=Path(__file__).resolve().parent
COMPONENTS={'handle':['fix','fill','fdig','fret','relevel','reuse'],
            'generic':['gen','help','hdig'],'column':['dig','lift','ret'],
            'repair':['repair']}

def main():
    p=argparse.ArgumentParser();p.add_argument('--mode',default='filler')
    p.add_argument('--iterations',type=int,default=200);p.add_argument('--leaves',type=int,default=15)
    p.add_argument('--final',action='store_true');p.add_argument('--name',default='target')
    a=p.parse_args();d=load(a.mode);tags=d['tags'];seeds=d['seeds']
    if a.final:
        frozen_spec=json.loads((HERE/'models'/(a.name+'.validation.json')).read_text())
        assert (a.mode,a.iterations,a.leaves)==(frozen_spec['mode'],frozen_spec['iterations'],frozen_spec['leaves'])
    fs=[np.load(HERE/'data'/(v+'.'+a.mode+'.npz')) for v in tags]
    raw=[np.load(HERE/'data'/(v+'.npz')) for v in tags]
    X=np.stack([f['T'] for f in fs],axis=1).astype(np.float32)
    names=fs[0]['tnames'].tolist()
    counts=np.stack([r['counts'] for r in raw],axis=1)
    labs=np.stack([r['target_labels'] for r in raw],axis=1)
    print('target features',X.shape,'labels',labs.shape,flush=True)
    # Restrict the enormous feature grid to the representative physical model;
    # these choices are fixed before the validation result is observed.
    keep=[i for i,n in enumerate(names) if not n.startswith(('f_','m_')) or n.startswith(('f_s2_p1.6_','m_s2_it4_'))]
    X=X[:,:,:,keep];names=[names[i] for i in keep]
    ncase,ndesign,ntarget,nfeat=X.shape
    train=seeds<(500 if a.final else 400)
    valid=(seeds>=400)&(seeds<500)
    preds=np.zeros((ncase,ndesign,len(COMPONENTS)))
    oof=np.zeros_like(preds)
    md=HERE/'models';md.mkdir(exist_ok=True)
    for ci,(name,labelset) in enumerate(COMPONENTS.items()):
        inds=[d['label_names'].index(l) for l in labelset]
        response=labs[:,:,:,inds].sum(axis=-1)/np.maximum(1,counts)
        for fold in range(3):
            if fold<2:
                tr=train & ((seeds%2)!=fold);te=train & ((seeds%2)==fold)
            else:tr=train;te=np.ones(ncase,dtype=bool)
            m=HistGradientBoostingRegressor(max_iter=a.iterations,max_leaf_nodes=a.leaves,
                learning_rate=0.07,min_samples_leaf=200,l2_regularization=10,
                early_stopping=False,random_state=1969)
            m.fit(X[tr].reshape(-1,nfeat),response[tr].ravel(),sample_weight=counts[tr].ravel())
            pr=m.predict(X[te].reshape(-1,nfeat)).reshape(-1,ndesign,ntarget).mean(axis=2)
            if fold<2:oof[te,:,ci]=pr
            else:
                preds[:,:,ci]=pr
                joblib.dump(m,md/(a.name+'.'+name+('.final' if a.final else '')+'.joblib'))
            print('fitted',name,'fold',fold,flush=True)
    DX=d['X'];dn=d['names']
    # Keep design correction modest; components already express nonlinear target interactions.
    keep=[i for i,n in enumerate(dn) if n in ['col','gc','h2_d0','h2_d1','h2_last1','h2_balance','h2_balance2']]
    z=np.concatenate([DX[:,:,keep],preds],axis=2)
    ztrain=z.copy();ztrain[train,:,len(keep):]=oof[train]
    zn=[dn[i] for i in keep]+['pred_'+n for n in COMPONENTS]
    y=d['Y'].mean(axis=2)
    best=-1;selected=None;grid=[]
    if a.final:
        frozen=json.loads((md/(a.name+'.validation.json')).read_text())
        alphas=[frozen['alpha']]
    else:alphas=[.1,1.,10.,100.,1000.]
    for alpha in alphas:
        co,bias=linear_fit(ztrain[train],y[train],alpha)
        pred=z@co+bias
        mt=group_metrics(pred[valid],d['Y'][valid],tags)
        grid.append({'alpha':alpha,'metrics':mt})
        if mt['all']['r']>best:best=mt['all']['r'];selected=alpha,co,bias,pred,mt
    alpha,co,bias,pred,mt=selected
    if a.final:
        test=(seeds>=500)&(seeds<1000)
        mt=group_metrics(pred[test],d['Y'][test],tags)
    results={'variants':tags,'models':{a.name:mt},'grid':grid}
    print(summarize(a.name,mt),flush=True)
    spec={'name':a.name,'mode':a.mode,'alpha':alpha,'feature_names':zn,'target_features':names,
          'coefficients':co.tolist(),'intercept':bias,'iterations':a.iterations,'leaves':a.leaves}
    suffix='final' if a.final else 'validation'
    (md/(a.name+'.'+suffix+'.json')).write_text(json.dumps(spec,indent=2))
    (md/(a.name+('.test' if a.final else '.metrics')+'.json')).write_text(json.dumps(results,indent=2))
    np.savez_compressed(md/(a.name+'.'+suffix+'.npz'),pred=pred,components=preds,oof=oof,
                        seed=seeds,variant=tags,component_names=list(COMPONENTS))

if __name__=='__main__':main()
