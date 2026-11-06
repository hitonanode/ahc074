"""Compress the expensive quadrature grid using training/validation seeds only.

Candidate blocks are fixed physical settings; all designs, not individual target
rows, are the held-out unit. This is cost/accuracy selection within the filler idea.
"""
import os
os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
os.environ.setdefault('OMP_NUM_THREADS','1')
import sys
sys.dont_write_bytecode=True
from pathlib import Path
import json
import itertools
import numpy as np
from fit import load,linear_fit,group_metrics,summarize

HERE=Path(__file__).resolve().parent
d=load('filler');X=d['X'];y=d['Y'].mean(axis=2);names=d['names']
tr=d['seeds']<400;va=(d['seeds']>=400)&(d['seeds']<500)
base=[i for i,n in enumerate(names) if not n.startswith('f_')]
configs=[f'f_s{s}_p{p:g}_' for s in (0,1,2,4) for p in (1.,1.6,2.2)]
# Single blocks, and pairs sharing the same head probabilities / donor table.
choices=[(c,) for c in configs]+[pair for pair in itertools.combinations(configs,2) if pair[0].split('_p')[0]==pair[1].split('_p')[0]]
results=[]
for cc in choices:
    strengths={c.split('_p')[0] for c in cc}
    ids=base+[i for i,n in enumerate(names) if any(n.startswith(c) for c in cc) or n in {s+'_headutility' for s in strengths}]
    xx=X[:,:,ids];best=None
    for alpha in (1.,10.,100.,1000.):
        coef,bias=linear_fit(xx[tr],y[tr],alpha)
        pred=xx@coef+bias
        mt=group_metrics(pred[va],d['Y'][va],d['tags'])
        if best is None or mt['all']['r']>best['metrics']['all']['r']:
            best={'configs':cc,'alpha':alpha,'feature_names':[names[i] for i in ids],
                  'coefficients':coef.tolist(),'intercept':bias,'metrics':mt}
    results.append(best)
results.sort(key=lambda r:-r['metrics']['all']['r'])
(HERE/'models/config_selection.json').write_text(json.dumps({'variants':d['tags'],'results':results},indent=2))
for r in results[:12]: print(r['configs'],'alpha',r['alpha'],summarize('compressed',r['metrics']),flush=True)
