from pathlib import Path
import json,math
P=Path(__file__).resolve().parent;R=Path('/home/sato/ahc074/runs/20261107-185215_deval-shortplus5')
assert json.loads((R/'meta.json').read_text())['status']=='ok'
rows=[]
for order in range(2):
    ep=R/('err' if order==0 else f'orders/{order}/err')
    for f in sorted(ep.glob('*.txt')):
        seed=int(f.stem);assert seed<200
        for line in f.read_text().splitlines():
            if not line.startswith('#f2plan '):continue
            a=line.split()
            if int(a[4])-int(a[10])==1:
                rows.append((seed,float(a[6]),max(0.,float(a[8])),int(a[9]),int(a[11]),int(a[12])))
out={'run':R.name,'n_rows':len(rows),'splits':{}}
for lo,hi in [(0,100),(100,200)]:
    r=[x for x in rows if lo<=x[0]<hi]
    base=sum(x[2] for x in r);z=[]
    for gap in [0,.25,.5,.75,1,1.25,1.5,2,3,10]:
        kept=[x for x in r if x[1]<=gap]
        z.append({'gap':gap,'fraction_calls':len(kept)/len(r),'fraction_gain':sum(x[2] for x in kept)/base,'won':sum(x[3] for x in kept),'n':len(kept)})
    out['splits'][f'{lo}-{hi}']={'all_calls':len(r),'all_gain':base,'all_won':sum(x[3] for x in r),'thresholds':z}
(P/'shorttrace.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
