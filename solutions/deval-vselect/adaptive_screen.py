"""Validation-only allocation of finishing calls, using the 25-snapshot pool."""
from pathlib import Path
import json
import numpy as np
HERE=Path(__file__).resolve().parent
d=np.load(HERE/'prescreen_data.npz')
spec=json.loads((HERE/'prescreen_head_state.validation.json').read_text())
mask=d['seeds']>=400
X=d['X'][mask];y=d['y'][mask]
w=X[:,:,:len(spec['coefficients'])]@np.asarray(spec['coefficients'])+spec['intercept']
rank=np.argsort(w,axis=1)
order_y=np.take_along_axis(y,rank,axis=1)
order_w=np.take_along_axis(w,rank,axis=1)
out=[]
for k in [1,2,3,4,5,6,8,12,25]:
    delta=order_y[:,:k].min(axis=1)-y[:,-1]
    item=dict(kind='fixed',k=k,n=k,gain=float(delta.mean()))
    out.append(item);print(item,flush=True)
for limit in [6,8,12,25]:
    for margin in [0.,.002,.005,.01,.015,.02,.03,.04,.06,.08]:
        delta=[];counts=[]
        for yy,ww,baseline in zip(order_y,order_w,y[:,-1]):
            best=1e100
            for i in range(limit):
                if i>=2:
                    offset=np.mean(yy[:i]-ww[:i])
                    if ww[i]+offset>best+margin:break
                best=min(best,yy[i])
            else:i=limit
            delta.append(best-baseline);counts.append(i)
        item=dict(kind='adaptive',limit=limit,margin=margin,n=float(np.mean(counts)),gain=float(np.mean(delta)))
        out.append(item)
        if 2<=item['n']<=6:print(item,flush=True)
(HERE/'adaptive_screen.json').write_text(json.dumps(out,indent=2))
