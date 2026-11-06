"""One final test evaluation after FROZEN.json fixes models and parameters.

Run under flock. This script never selects a model or tunes a coefficient on test
seeds. It refits frozen linear specifications on seeds 0..499 and reports 500..999.
The target learner is finalized separately with its already frozen parameters.
"""
import os
os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
os.environ.setdefault('OMP_NUM_THREADS','1')
import sys
sys.dont_write_bytecode=True
from pathlib import Path
import json
import numpy as np
from fit import load,linear_fit,group_metrics,summarize,ORDER

HERE=Path(__file__).resolve().parent
MODELS=HERE/'models'

def main():
    frozen=json.loads((HERE/'FROZEN.json').read_text())
    specs=frozen['linear_models']
    cache={}
    result={'selected_model':frozen['selected_model'],'frozen':frozen,'models':{}}
    predictions={}
    for name in specs:
        spec=json.loads((MODELS/(name+'.validation.json')).read_text())
        mode=spec['mode']
        assert mode==frozen['validation'][name]['mode']
        assert spec['alpha']==frozen['validation'][name]['alpha'], 'frozen hyperparameter changed'
        if mode not in cache:cache[mode]=load(mode)
        d=cache[mode]
        assert d['tags']==ORDER
        assert np.array_equal(d['seeds'],np.arange(1000))
        names=spec['feature_names']
        if spec.get('feature_set')=='baseline' or name=='baseline_calibrated':
            X=d['B'][:,:,[d['bnames'].index(n) for n in names]]
        else:X=d['X'][:,:,[d['names'].index(n) for n in names]]
        train=d['seeds']<500;test=d['seeds']>=500
        y=d['Y'].mean(axis=2)
        coef,bias=linear_fit(X[train],y[train],spec['alpha'])
        pred=X@coef+bias
        spec.update(coefficients=coef.tolist(),intercept=bias,training_seeds='0-499',variants=d['tags'])
        (MODELS/(name+'.final.json')).write_text(json.dumps(spec,indent=2))
        result['models'][name]=group_metrics(pred[test],d['Y'][test],d['tags'])
        predictions[name]=pred
        print(summarize(name,result['models'][name]),flush=True)
    d=next(iter(cache.values()));test=d['seeds']>=500
    for j,name in enumerate(d['bnames'][:5]):
        result['models'][name]=group_metrics(d['B'][test,:,j],d['Y'][test],d['tags'])
        predictions[name]=d['B'][:,:,j]
    target=MODELS/'target_fast.test.json'
    if frozen.get('target_model'):
        assert target.exists()
        tm=json.loads(target.read_text())
        assert tm['variants']==ORDER
        result['models'].update(tm['models'])
        predictions['target_fast']=np.load(MODELS/'target_fast.final.npz')['pred']
    # Independent-case bootstrap of correlation is descriptive only, after freezing.
    rng=np.random.default_rng(20261107)
    for name in [frozen['selected_model'],'model_cost']:
        pred=predictions[name][test];y=d['Y'][test].mean(axis=2)
        pc=pred-pred.mean(axis=1,keepdims=True);yc=y-y.mean(axis=1,keepdims=True)
        boots=[]
        for _ in range(2000):
            ix=rng.integers(len(y),size=len(y))
            boots.append(float(np.corrcoef(pc[ix].ravel(),yc[ix].ravel())[0,1]))
        result['models'][name]['all']['r_bootstrap_se']=float(np.std(boots,ddof=1))
        result['models'][name]['all']['r_bootstrap_ci95']=np.quantile(boots,[.025,.975]).tolist()
    np.savez_compressed(MODELS/'final_predictions.npz',**predictions,seeds=d['seeds'],variants=d['tags'],Y=d['Y'])
    (HERE/'TEST_RESULTS.json').write_text(json.dumps(result,indent=2))

if __name__=='__main__':main()
