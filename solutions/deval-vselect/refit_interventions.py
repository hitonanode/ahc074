"""Teach the surrogate about completed designs that fooled the original V.

Use only seed 0--399 for fitting and 400--499 for selection. Execute after
refit_branch.py, under runs/.lock. This is a 142-term linear model as before.
"""
from pathlib import Path
import json,subprocess
import numpy as np
from refit_branch import HERE,RUNS,MODEL,state_file,family_fit,selection

def main():
    manifest={r['tag']:r for r in map(json.loads,(HERE/'experiments.jsonl').read_text().splitlines())}
    tags=['refine32','refinebatch','vmatch6','targetmatch4','col24','local05']
    prior=np.load(HERE/'target_cv_qmc_16.npz');branch=np.load(HERE/'branch_training.npz')
    names=prior['names'].tolist()
    cache=HERE/'intervention_training.npz'
    if cache.exists():
        d=np.load(cache);X,Y=d['X'],d['Y']
    else:
        paths=[str(state_file(manifest[tag]['design'],s)) for s in range(500) for tag in tags]
        raw=subprocess.run([str(HERE/'branch_features'),'16'],input=('\n'.join(paths)+'\n').encode(),capture_output=True,check=True).stdout
        X=np.frombuffer(raw,dtype=np.float64).reshape(500,len(tags),len(names))
        ys=[]
        for tag in tags:
            cases={int(c['seed']):c for c in json.loads((RUNS/manifest[tag]['replay']/'result.json').read_text())['cases']}
            ys.append([cases[s]['order_scores'] for s in range(500)])
        Y=np.transpose(np.asarray(ys,float),(1,0,2))/1024
        X=np.concatenate([prior['X'][:,:1],X],axis=1)
        Y=np.concatenate([prior['Y'][:,:1],Y],axis=1)
        np.savez_compressed(cache,X=X,Y=Y,names=names,tags=['base']+tags)
    bx,by=branch['X'],branch['Y'];base=prior['Y'][:,0]
    families=[(prior['X'],prior['Y'][:,:,1:]),(X,Y[:,:,1:]),(bx,by[:,:,1:])]
    results={'grid':[]};best=None
    for original in [.25,1.,4.]:
        for intervention in [.25,1.,4.,16.]:
            for alpha in [1.,10.,100.,1000.,10000.]:
                weights=[original,intervention,1.]
                coef,bias=family_fit(families,weights,alpha,400)
                m=selection(bx[400:]@coef+bias,by[400:],base[400:])
                row=dict(weights=weights,alpha=alpha,metrics=m)
                results['grid'].append(row)
                if best is None or m['r']>best[0]:best=(m['r'],weights,alpha,coef,bias,m)
    _,weights,alpha,coef,bias,m=best
    spec=dict(feature_names=names,coefficients=coef.tolist(),intercept=bias,family_weights=weights,alpha=alpha,
              metrics=m,training_seeds='0-399',validation_seeds='400-499',interventions=tags,n_samples=16)
    (HERE/'intervention_model.validation.json').write_text(json.dumps(spec,indent=2))
    print('selected',weights,alpha,m,flush=True)
    results['selected']=spec.copy()
    coef,bias=family_fit(families,weights,alpha,500)
    spec.update(coefficients=coef.tolist(),intercept=bias,training_seeds='0-499')
    (HERE/'intervention_model.final.json').write_text(json.dumps(spec,indent=2))
    results['fitted_500']=selection(bx@coef+bias,by,base)
    print('fit 500 (in sample)',results['fitted_500'],flush=True)
    (HERE/'intervention_refit_results.json').write_text(json.dumps(results,indent=2))
if __name__=='__main__':main()
