"""Calibrate V on completed late branches, using only seeds 0--499.

Run under runs/.lock. Families are centered separately: original independent
restarts and the four short late branches. Hyperparameters see 400--499 only.
"""
from pathlib import Path
import json,sys,subprocess,re
import numpy as np
from sklearn.linear_model import Ridge
HERE=Path(__file__).resolve().parent
MODEL=HERE.parent/'deval-model'
RUNS=Path('/home/sato/ahc074/runs')
sys.path.insert(0,str(MODEL))
from prepare import state_file
from metrics import center,corr,metrics
from target_qmc import independent_samples,control_variates

def build_features():
    source=control_variates(independent_samples((MODEL/'surrogate.hpp').read_text()))
    (HERE/'branch_surrogate.hpp').write_text(source)
    source=(MODEL/'design_features.hpp').read_text().replace('"surrogate.hpp"','"branch_surrogate.hpp"')
    for h in ['poset_data.hpp','quadrature.hpp']:
        source=source.replace('"'+h+'"','"../deval-model/'+h+'"')
    (HERE/'branch_features.hpp').write_text(source)
    source=(MODEL/'value.hpp').read_text().replace('"design_features.hpp"','"branch_features.hpp"')
    (HERE/'branch_value.hpp').write_text(source)
    source=(HERE/'features_target.cpp').read_text().replace('"value_target.hpp"','"branch_value.hpp"')
    (HERE/'branch_features.cpp').write_text(source)
    subprocess.run(['g++','-std=c++23','-O2','-mpopcnt',str(HERE/'branch_features.cpp'),'-o',str(HERE/'branch_features')],check=True)

def family_fit(families,weights,alpha,n):
    xx=[];yy=[]
    for (X,Y),w in zip(families,weights):
        if not w:continue
        # Equalize family mass, independently of the number of its candidates.
        z=(w/X.shape[1])**.5
        xx.append(center(X[:n]).reshape(-1,X.shape[-1])*z)
        yy.append(center(Y[:n].mean(axis=2)).ravel()*z)
    x=np.concatenate(xx);y=np.concatenate(yy)
    scale=np.sqrt((x*x).mean(axis=0));scale[scale<1.e-10]=1
    model=Ridge(alpha=alpha,fit_intercept=False).fit(x/scale,y)
    coef=model.coef_/scale
    X,Y=families[-1]
    return coef,float(Y[:n].mean()-X[:n].mean(axis=(0,1))@coef)

def selection(pred,Y,base):
    yy=Y[:,:,1:8].mean(axis=2);pick=np.argmin(pred,axis=1)
    d=100*np.log(yy[np.arange(len(yy)),pick]/base[:,1:8].mean(axis=1))
    return dict(r=corr(center(pred),center(yy)),gain=float(d.mean()),se=float(d.std(ddof=1)/len(d)**.5))

def main():
    manifest={r['tag']:r for r in map(json.loads,(HERE/'experiments.jsonl').read_text().splitlines())}
    runs=[manifest[f'trainbranch{i}'] for i in range(4)]
    prior=np.load(HERE/'target_cv_qmc_16.npz')
    names=prior['names'].tolist()
    cache=HERE/'branch_training.npz'
    if cache.exists():
        data=np.load(cache);X,Y=data['X'],data['Y']
    else:
        build_features()
        paths=[str(state_file(r['design'],s)) for s in range(500) for r in runs]
        raw=subprocess.run([str(HERE/'branch_features'),'16'],input=('\n'.join(paths)+'\n').encode(),capture_output=True,check=True).stdout
        X=np.frombuffer(raw,dtype=np.float64).reshape(500,4,len(names))
        arrays=[]
        for r in runs:
            cases={int(c['seed']):c for c in json.loads((RUNS/r['replay']/'result.json').read_text())['cases']}
            arrays.append([cases[s]['order_scores'] for s in range(500)])
        Y=np.transpose(np.asarray(arrays,float),(1,0,2))/1024
        assert np.all(Y>0)
        np.savez_compressed(cache,X=X,Y=Y,names=names)
    families=[(prior['X'],prior['Y'][:,:,1:8]),(X,Y[:,:,1:8])]
    base=prior['Y'][:,0]
    old=json.loads((HERE/'target_cv_qmc_16.validation.json').read_text())
    pc=np.asarray(old['coefficients']);pb=old['intercept']
    results={'prior_validation':selection(X[400:]@pc+pb,Y[400:],base[400:]),'grid':[]}
    print('prior validation',results['prior_validation'],flush=True)
    best=None
    for weight in [0.,.25,1.,4.,16.]:
        for alpha in [.1,1.,10.,100.,1000.,10000.]:
            coef,bias=family_fit(families,[weight,1.],alpha,400)
            pred=X[400:]@coef+bias
            m=selection(pred,Y[400:],base[400:])
            record=dict(original_weight=weight,alpha=alpha,metrics=m)
            results['grid'].append(record)
            if best is None or m['r']>best[0]:best=(m['r'],weight,alpha,coef,bias,m)
    _,weight,alpha,coef,bias,m=best
    print('selected',weight,alpha,m,flush=True)
    spec=dict(feature_names=names,coefficients=coef.tolist(),intercept=bias,original_weight=weight,alpha=alpha,
              metrics=m,source_runs=runs,training_seeds='0-399',validation_seeds='400-499',n_samples=16)
    (HERE/'branch_model.validation.json').write_text(json.dumps(spec,indent=2))
    results['selected']=spec
    coef,bias=family_fit(families,[weight,1.],alpha,500)
    spec.update(coefficients=coef.tolist(),intercept=bias,training_seeds='0-499')
    (HERE/'branch_model.final.json').write_text(json.dumps(spec,indent=2))
    oldfinal=json.loads((HERE.parent/'deval-vtarget/V.json').read_text())
    results['old_fitted_500']=selection(X@np.asarray(oldfinal['coefficients'])+oldfinal['intercept'],Y,base)
    results['new_fitted_500']=selection(X@coef+bias,Y,base)
    results['oracle_4_4']=selection(Y[:,:,:4].mean(axis=2),np.repeat(Y[:,:,4:8].mean(axis=2)[:,:,None],8,axis=2),
        np.repeat(base[:,4:8].mean(axis=1)[:,None],8,axis=1))
    print('old fit 500',results['old_fitted_500'],'new fit 500 (in sample)',results['new_fitted_500'],flush=True)
    print('cross-list oracle',results['oracle_4_4'],flush=True)
    (HERE/'branch_refit_results.json').write_text(json.dumps(results,indent=2))

if __name__=='__main__':main()
