"""Fit finishing-value prediction after one Hungarian round, training seeds only."""
from pathlib import Path
import sys,re,json
import numpy as np
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'deval-model'))
from fit import linear_fit
from metrics import corr,center

def main():
    run=sys.argv[1];rows=[];labels=[];seeds=[]
    for path in sorted(Path('/home/sato/ahc074/runs',run,'err').glob('*.txt')):
        seed=int(path.stem);assert 0<=seed<500
        text=path.read_text()
        x={int(i):np.fromstring(v,sep=' ') for i,v in re.findall(r'^@deval_raw (\d+) (.*)$',text,re.M)}
        y={int(i):float(v) for i,v in re.findall(r'^@deval_final (\d+) (\S+)$',text,re.M)}
        if len(x)!=12 or len(y)!=12:continue
        rows.append([x[i] for i in range(12)]);labels.append([y[i] for i in range(12)]);seeds.append(seed)
    X=np.asarray(rows);Y=np.asarray(labels);seeds=np.array(seeds)
    assert len(X)==500 and X.shape[-1]==142,X.shape
    spec=json.loads((HERE.parent/'deval-vtarget/V.json').read_text())
    train=seeds<400;val=seeds>=400
    def metrics(pred):
        y=Y[val];p=pred[val]
        out={'r':corr(center(p).ravel(),center(y).ravel())}
        for k in [1,2,3,4]:
            ids=np.argsort(p,axis=1)[:,:k]
            gap=np.take_along_axis(y,ids,axis=1).min(axis=1)-y.min(axis=1)
            out[f'gap{k}']=[float(gap.mean()),float(gap.std(ddof=1)/len(gap)**.5)]
        return out
    old=metrics(X@np.array(spec['coefficients'])+spec['intercept'])
    print('old validation',old,flush=True)
    grid=[];best=None
    for alpha in [.01,.1,1.,10.,100.,1000.,10000.]:
        coef,bias=linear_fit(X[train],Y[train],alpha)
        m=metrics(X@coef+bias);grid.append({'alpha':alpha,'metrics':m})
        if best is None or m['r']>best[0]:best=(m['r'],alpha,coef,bias,m)
    _,alpha,coef,bias,m=best
    out=dict(feature_names=spec['feature_names'],coefficients=coef.tolist(),intercept=bias,
             alpha=alpha,metrics=m,training_seeds='0-399',validation_seeds='400-499',source_run=run)
    (HERE/'screen_model.validation.json').write_text(json.dumps(out,indent=2))
    coef,bias=linear_fit(X,Y,alpha)
    out.update(coefficients=coef.tolist(),intercept=bias,training_seeds='0-499')
    (HERE/'screen_model.final.json').write_text(json.dumps(out,indent=2))
    (HERE/'screen_fit_results.json').write_text(json.dumps({'old':old,'grid':grid,'selected':m},indent=2))
    np.savez_compressed(HERE/'screen_training.npz',X=X,Y=Y,seeds=seeds,names=spec['feature_names'])
    print('selected',alpha,m,flush=True)
if __name__=='__main__':main()
