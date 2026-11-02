"""Check every public barcode using all 192 actual 64-window paper patterns.

This is a representability check, not an efficient online policy. Choosing an
arbitrary paper that agrees on all still-uncovered windows is safe: it only
removes constraints on later papers. Hence this greedy check is complete for
existence of a displaying permutation, with the designated paper fixed first.
"""
import sys
sys.dont_write_bytecode=True
import json
from resident_probe import Resident,HERE
from borrowed_port import Borrowed
from routing_search import Data

def change(papers,k,windows,op,black):
    physical=lambda m:sum(((m>>i)&1)<<w for i,w in enumerate(windows))
    mask=sum(1<<w for w in windows)
    before_op,before_black=papers[k]
    papers[k]=(before_op&~mask|physical(op),before_black&~mask|physical(black))

def actual(data,kind,borrowed=False):
    papers=[(p.opaque,p.black) for p in data.out.designs]
    if isinstance(data,Data):
        masks=data.masks(kind);windows=data.hs[25:]
        for k in data.members:change(papers,k,windows,masks[k],masks[k]&data.colors[k])
    else:
        windows=data.hs[data.first:]
        if borrowed:
            windows=windows+[data.port]
            papers=[(op&~(1<<data.port),b&~(1<<data.port)) for op,b in papers]
        rows=data.make(kind,1,False).splitlines()
        members=data.members if kind=='baseline' else data.regular+data.ctrl
        for k,row in zip(members,rows[1:]):
            op,b=map(int,row.split()[:2]);change(papers,k,windows,op,b)
    return papers

def check(data,papers):
    assert len(papers)==192 and all(op for op,b in papers)
    failures=[]
    for u,target in enumerate(data.inp.target):
        d=data.ded[u];cov,black=papers[d]
        if (black^target)&cov:failures.append(u);continue
        todo=[k for k in range(192) if k!=d]
        while todo:
            rest=[]
            for k in todo:
                op,b=papers[k]
                if ((b^target)&op&~cov)==0:black|=b&~cov;cov|=op
                else:rest.append(k)
            if len(rest)==len(todo):break
            todo=rest
        if todo or black!=target:failures.append(u)
    return dict(products=256,failures=failures,N=64,K=192,P=256)

if __name__=='__main__':
    rows=[]
    chosen=json.loads((HERE/'validation_0_40_64.json').read_text())['records']
    for r in chosen:
        data=Data(r['seed']);result=check(data,actual(data,r['selected']))
        rows.append(dict(seed=r['seed'],kind='routing:'+r['selected'],**result))
    for seed in range(8):
        for h in (4,28):
            data=Resident(seed,h)
            for kind in ('full','split','short'):
                rows.append(dict(seed=seed,kind=f'resident{h}:{kind}',**check(data,actual(data,kind))))
        data=Borrowed(seed)
        for kind in ('full','split','short'):
            rows.append(dict(seed=seed,kind='borrowed:'+kind,**check(data,actual(data,kind,True))))
    result={'designs':len(rows),'products_tested':256*len(rows),
        'unrepresentable':sum(len(r['failures']) for r in rows),'records':rows}
    (HERE/'physical_feasibility.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='records'},indent=2))
