"""Design-level, seed-clustered evaluation. Lower costs and differences are better."""
import numpy as np

def center(x):
    return x - x.mean(axis=1, keepdims=True)

def corr(x,y):
    return float(np.corrcoef(np.asarray(x).ravel(), np.asarray(y).ravel())[0,1])

def mean_se(x):
    x=np.asarray(x)
    return [float(x.mean()),float(x.std(ddof=1)/np.sqrt(len(x)))]

def metrics(v, scores, base=0):
    """v: [seed,design], scores: [seed,design,list]. Always select by v only.

    The oracle selects on lists 0..3 and is scored on lists 4..7. Random means
    the expectation of a uniform pick among the SAME design set (including base).
    Percent effects are the mean of paired per-case ratios, not ratio of means.
    """
    n,d,q=scores.shape
    y=scores.mean(axis=2)
    a=scores[:,:,:4].mean(axis=2)
    b=scores[:,:,4:].mean(axis=2)
    half=corr(center(a),center(b))
    rel=2*half/(1+half)
    r=corr(center(v),center(y))
    pick=np.argmin(v,axis=1)
    oi=np.argmin(a,axis=1)
    sel=y[np.arange(n),pick]
    selb=b[np.arange(n),pick]
    oracle=b[np.arange(n),oi]
    out=dict(n=n,designs=d,r=r,reliability=rel,half_correlation=half,
             r_corrected=r/np.sqrt(rel),mean_cost=float(y.mean()))
    for name,p,ref in [('base',sel,y[:,base]),('random',sel,y.mean(axis=1)),
                       ('base_half',selb,b[:,base]),('random_half',selb,b.mean(axis=1)),
                       ('oracle_base',oracle,b[:,base]),('oracle_random',oracle,b.mean(axis=1))]:
        out[name]=mean_se(p-ref)
        out[name+'_pct']=mean_se(100*(p-ref)/ref)
    out['pick_histogram']=np.bincount(pick,minlength=d).tolist()
    out['calibration_bias']=float((v-y).mean())
    out['rmse']=float(np.sqrt(np.mean((v-y)**2)))
    dv,dy=center(v),center(y)
    out['within_rmse']=float(np.sqrt(np.mean((dv-dy)**2)))
    out['calibration_slope']=float(np.sum(dv*dy)/np.sum(dv*dv))
    return out

GROUPS={'all':[0,1,2,3,4,5,6],'full':[0,1,2,3],'anneal':[0,4,5,6]}

def report_groups(v,scores):
    return {name:metrics(v[:,ids],scores[:,ids]) for name,ids in GROUPS.items()}
