"""Seed-disjoint fitting. Default: training 0..399, validation 400..499.

No test metrics are computed without --final. Hyperparameter selection uses only
validation seeds. The selected model files contain the exact feature formula and
linear coefficients needed for a deterministic evaluator of an individual design.
"""
import os
for k in ('OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','OMP_NUM_THREADS'):
    os.environ.setdefault(k,'1')
import sys
sys.dont_write_bytecode=True
import argparse
import json
from pathlib import Path
import numpy as np
from sklearn.linear_model import Ridge
from sklearn.ensemble import HistGradientBoostingRegressor
import joblib
from metrics import center,metrics,corr

HERE=Path(__file__).resolve().parent
DATA=HERE/'data'
ORDER=['base','DESIGN_SEED_1','DESIGN_SEED_2','DESIGN_SEED_3','DSEED_A_1','DSEED_A_2','DSEED_A_3']

def load(mode='static'):
    tags=[v for v in ORDER if (DATA/(v+'.'+mode+'.npz')).exists()]
    assert len(tags)>=2, 'At least two designs are needed for within-case prediction.'
    raw=[np.load(DATA/(v+'.npz')) for v in tags]
    fs=[np.load(DATA/(v+'.'+mode+'.npz')) for v in tags]
    seeds=raw[0]['seeds']
    assert all(np.array_equal(r['seeds'],seeds) for r in raw)
    assert all(np.array_equal(f['names'],fs[0]['names']) for f in fs)
    return dict(tags=tags,seeds=seeds,Y=np.stack([r['scores'] for r in raw],axis=1),
                B=np.stack([r['baselines'] for r in raw],axis=1),bnames=raw[0]['baseline_names'].tolist(),
                X=np.stack([f['X'] for f in fs],axis=1).astype(float),names=fs[0]['names'].tolist(),
                labels=np.stack([r['list_labels'] for r in raw],axis=1),
                label_names=raw[0]['label_names'].tolist())

def group_metrics(pred,Y,tags):
    groups={'all':list(range(len(tags))),
            'full':[i for i,v in enumerate(tags) if v=='base' or v.startswith('DESIGN_')],
            'anneal':[i for i,v in enumerate(tags) if v=='base' or v.startswith('DSEED_')]}
    return {k:metrics(pred[:,ids],Y[:,ids]) for k,ids in groups.items() if len(ids)>1}

def linear_fit(X,y,alpha):
    xc=center(X);yc=center(y)
    scale=np.sqrt(np.mean(xc**2,axis=(0,1)))
    scale[scale<1.e-10]=1
    m=Ridge(alpha=alpha,fit_intercept=False)
    m.fit((xc/scale).reshape(-1,X.shape[-1]),yc.ravel())
    coef=m.coef_/scale
    intercept=float(y.mean()-np.mean(X,axis=(0,1))@coef)
    return coef,intercept

def summarize(name,result):
    lines=[]
    for group,mt in result.items():
        lines.append(f"{name:26s} {group:7s} r={mt['r']:.4f} corrected={mt['r_corrected']:.4f} "
                     f"base={mt['base'][0]:+.5f} +/- {mt['base'][1]:.5f} "
                     f"random={mt['random'][0]:+.5f} +/- {mt['random'][1]:.5f}")
    return '\n'.join(lines)

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--mode',default='static',choices=['static','filler','markov','fast','compact','stationary','stationary32','persistent'])
    p.add_argument('--final',action='store_true')
    p.add_argument('--name',default=None)
    p.add_argument('--feature-set',default='all',choices=['all','minimal','baseline','head','coupled'])
    a=p.parse_args();d=load(a.mode)
    experiment=a.name or (a.mode+'_'+a.feature_set)
    train=d['seeds']<400;val=(d['seeds']>=400)&(d['seeds']<500)
    y=d['Y'].mean(axis=2)
    X=d['X'];names=d['names']
    if a.feature_set=='baseline':X=d['B'];names=d['bnames']
    if a.feature_set=='minimal':
        keep=[i for i,n in enumerate(names) if n in ['col','gc','h2_d0','h2_d1','h2_last1','h2_balance','h2_balance2']]
        X=X[:,:,keep];names=[names[i] for i in keep]
    if a.feature_set in ('head','coupled'):
        base=['col','gc','h2_d0','h2_d1','h2_last1','h2_balance','h2_balance2','f_s2_headutility']
        keep=[i for i,n in enumerate(names) if n in base or (a.feature_set=='coupled' and n.startswith('f_s2_p1.6_'))]
        X=X[:,:,keep];names=[names[i] for i in keep]
    results={'variant_names':d['tags'],'mode':a.mode,'feature_set':a.feature_set,'models':{}}
    for i,n in enumerate(d['bnames'][:5]):
        mt=group_metrics(d['B'][val,:,i],d['Y'][val],d['tags'])
        results['models'][n]=mt
        print(summarize(n,mt),flush=True)
    best=-1;chosen=None;grid=[]
    for alpha in (0.01,0.1,1.,10.,100.,1000.,10000.):
        coef,bias=linear_fit(X[train],y[train],alpha)
        pred=X@coef+bias
        mt=group_metrics(pred[val],d['Y'][val],d['tags'])
        grid.append({'alpha':alpha,'metrics':mt})
        r=mt['all']['r']
        if r>best:best=r;chosen=(alpha,coef,bias,mt)
    alpha,coef,bias,mt=chosen
    results['models'][experiment]=mt;results['grid']=grid
    results['selected_alpha']=alpha
    print('chosen alpha',alpha,flush=True)
    print(summarize(experiment,mt),flush=True)
    dest=HERE/'models';dest.mkdir(exist_ok=True)
    # Save every experiment's validation specification before any test is opened.
    spec={'experiment':experiment,'mode':a.mode,'feature_names':names,'alpha':alpha,
          'intercept':bias,'coefficients':coef.tolist(),'variants':d['tags'],
          'training_seeds':'0-399','validation_seeds':'400-499'}
    (dest/(experiment+'.validation.json')).write_text(json.dumps(spec,indent=2))
    (dest/(experiment+'.metrics.json')).write_text(json.dumps(results,indent=2))
    if a.final:
        # Final reporting should be orchestrated once all experiments are frozen.
        train=d['seeds']<500;test=(d['seeds']>=500)&(d['seeds']<1000)
        coef,bias=linear_fit(X[train],y[train],alpha)
        pred=X@coef+bias
        final={'variants':d['tags'],'models':{}}
        for i,n in enumerate(d['bnames'][:5]):final['models'][n]=group_metrics(d['B'][test,:,i],d['Y'][test],d['tags'])
        final['models'][experiment]=group_metrics(pred[test],d['Y'][test],d['tags'])
        spec.update(coefficients=coef.tolist(),intercept=bias,training_seeds='0-499')
        (dest/(experiment+'.final.json')).write_text(json.dumps(spec,indent=2))
        (dest/(experiment+'.test.json')).write_text(json.dumps(final,indent=2))
        print('FINAL TEST\n'+summarize(experiment,final['models'][experiment]),flush=True)
    importance=sorted(zip(names,coef,np.std(center(X[train]),axis=(0,1))*coef),key=lambda z:-abs(z[2]))
    print('largest standardized coefficients:',importance[:20],flush=True)

if __name__=='__main__':main()
