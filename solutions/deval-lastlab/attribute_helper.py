"""Read saved @ops only; attribute the training improvement to phases and move purposes."""
from pathlib import Path
import json,math,sys,collections
P=Path(__file__).resolve().parent;R=Path('/home/sato/ahc074/runs')
ref,run=sys.argv[1:3]
def mean(v):return sum(v)/len(v)
def se(v):m=mean(v);return (sum((x-m)**2 for x in v)/(len(v)-1)/len(v))**.5
def load(r):
    assert json.loads((R/r/'meta.json').read_text())['status']=='ok'
    return {int(c['seed']):c['order_scores'] for c in json.loads((R/r/'result.json').read_text())['cases']}
scores={r:load(r) for r in [ref,run]};rows=[]
for seed in range(500):
    data=[]
    for r in [ref,run]:
        counts=[0.]*1024;labels=collections.Counter()
        for order in range(1,4):
            path=R/r/f'orders/{order}/err/{seed:04d}.txt';seen=set();total=0
            with path.open() as f:
                for line in f:
                    if not line.startswith('@ops '):continue
                    parts=line.split();q=int(parts[1]);assert parts[2]=='=' and q not in seen;seen.add(q)
                    for token in parts[3:]:
                        name,sep,n=token.partition('*');n=int(n) if sep else 1
                        counts[q]+=n/3;labels[name]+=n/3;total+=n
            assert seen==set(range(1024)) and total==scores[r][seed][order],(r,seed,order,total)
        data.append((counts,labels))
    rows.append(data)
out={'reference':ref,'candidate':run,'seeds':[0,500],'lists':[1,4],'phases':[],'labels':{}}
for lo,hi in [(0,16),(16,64),(64,256),(0,256),(256,1024),(0,1024)]:
    v=[sum(b[0][lo:hi])-sum(a[0][lo:hi]) for a,b in rows]
    ratios=[100*math.log(sum(b[0][lo:hi])/sum(a[0][lo:hi])) for a,b in rows]
    out['phases'].append({'orders':[lo,hi],'moves_per_case':[mean(v),se(v)],'moves_per_order':[mean(v)/(hi-lo),se(v)/(hi-lo)],'percent':[mean(ratios),se(ratios)]})
names=sorted({k for row in rows for _,labels in row for k in labels})
for name in names:
    v=[(b[1][name]-a[1][name])/1024 for a,b in rows];out['labels'][name]=[mean(v),se(v)]
(P/'helper-attribution.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
