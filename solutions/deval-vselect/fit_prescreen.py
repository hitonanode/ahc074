"""Learn the finished V from an anneal snapshot, using training seeds only.

Pool labels are evaluations of finished states, never request-planner calls.
The heavy pool's independent replay measures the achievable score separately.
"""
from pathlib import Path
import sys,json,re
import numpy as np
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'deval-model'))
from fit import linear_fit
from metrics import corr,center

def main():
    run=sys.argv[1]
    rows=[];labels=[];seeds=[]
    for file in sorted(Path('/home/sato/ahc074/runs',run,'err').glob('*.txt')):
        seed=int(file.stem)
        assert seed<500
        text=file.read_text()
        raw={int(i):np.fromstring(v,sep=' ') for i,v in re.findall(r'^@deval_raw (\d+) (.*)$',text,re.M)}
        final={int(i):float(v) for i,v in re.findall(r'^@deval_final (\d+) (\S+)$',text,re.M)}
        if len(raw)!=25 or len(final)!=25:continue
        rows.append([raw[i] for i in range(25)])
        labels.append([final[i] for i in range(25)])
        seeds.append(seed)
    X=np.asarray(rows);y=np.asarray(labels);seeds=np.asarray(seeds)
    spec=json.loads((HERE.parent/'deval-model/models/stationary32_all.final.json').read_text())
    names=spec['feature_names']
    raw=X@np.asarray(spec['coefficients'])+spec['intercept']
    progress=np.broadcast_to(np.arange(25)[None,:,None]/24,(len(X),25,1))
    allX=np.concatenate([X,progress,progress**2,progress**3],axis=2)
    allnames=names+['progress','progress2','progress3']
    train=seeds<400;val=seeds>=400
    def metrics(pred,mask):
        yy=y[mask];p=pred[mask];out={'r':corr(center(p).ravel(),center(yy).ravel())}
        for k in [1,2,3,4]:
            selected=np.argsort(p,axis=1)[:,:k]
            v=np.take_along_axis(yy,selected,axis=1).min(axis=1)-yy[:,-1]
            out[f'gain{k}']=[float(v.mean()),float(v.std(ddof=1)/len(v)**.5)]
        return out
    results={'seeds':seeds.tolist(),'raw':metrics(raw,val),'models':{}}
    print('pool n',len(X),'raw validation',results['raw'],flush=True)
    head=names.index('f_s2_headutility')
    for name,keep in [('all',list(range(len(allnames)))),('head',list(range(head+1))+list(range(len(names),len(allnames)))),
                      ('static',list(range(head))+list(range(len(names),len(allnames)))),
                      ('all_state',list(range(len(names)))),('head_state',list(range(head+1))),('static_state',list(range(head)))]:
        xx=allX[:,:,keep]
        best=None
        for alpha in [.01,.1,1,10,100,1000,10000]:
            coef,bias=linear_fit(xx[train],y[train],alpha)
            m=metrics(xx@coef+bias,val)
            if best is None or m['r']>best[0]:best=(m['r'],alpha,coef,bias,m)
        _,alpha,coef,bias,m=best
        fitted={'feature_names':[allnames[k] for k in keep],'coefficients':coef.tolist(),'intercept':bias,'alpha':alpha,
                'metrics':m,'training_seeds':'0-399','validation_seeds':'400-499','source_run':run}
        (HERE/f'prescreen_{name}.validation.json').write_text(json.dumps(fitted,indent=2))
        coef,bias=linear_fit(xx,y,alpha)
        fitted.update(coefficients=coef.tolist(),intercept=bias,training_seeds='0-499')
        (HERE/f'prescreen_{name}.final.json').write_text(json.dumps(fitted,indent=2))
        results['models'][name]=m
        print(name,m,flush=True)
    np.savez_compressed(HERE/'prescreen_data.npz',X=X,y=y,seeds=seeds,names=names)
    (HERE/'prescreen_results.json').write_text(json.dumps(results,indent=2))
if __name__=='__main__':main()
