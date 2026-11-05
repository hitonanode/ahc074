"""Check discontinuous head-color changes in recorded whole-unit reassignments."""
import argparse
import json
import math
import statistics
import sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[1]/'scripts'))
import replay
RUNS=Path('/home/sato/ahc074/runs')
p=argparse.ArgumentParser()
p.add_argument('base');p.add_argument('candidates',nargs='+')
p.add_argument('--end',type=int,default=500)
p.add_argument('--output',default='whole-hole-groups.json')
a=p.parse_args()

def read(seed,run):
    h=0xcbf29ce484222325
    for t in replay.load_input(seed).target:
        for byte in t.to_bytes(8,'little'):h=((h^byte)*0x100000001b3)&((1<<64)-1)
    d={}
    for line in (RUNS/run/'design'/f'{h:016x}.txt').read_text().splitlines():
        key,*v=line.split()
        if key=='stderr':break
        if key in ['permutation','A','edge','polarity','papers','columns','ded','handle']:
            d[key]=list(map(int,v[1:]))
        else:d[key]=float(v[0]) if key=='end_sec' else int(v[0])
    counts=[[0,0]for _ in range(d['H'])];demands=[0]*d['H']
    for t,k in enumerate(d['ded']):
        demands[d['columns'][k]]+=1
        for j,window in enumerate(d['handle']):
            if not d['papers'][2*k]>>window&1:counts[j][d['A'][t]>>window&1]+=1
    prob=[(y+2*n*(y>x))/(x+y+2*n)for(x,y),n in zip(counts,demands)]
    return counts,prob

def stats(v):
    return {'n':len(v),'mean':statistics.mean(v)if v else 0,
            'se':statistics.stdev(v)/math.sqrt(len(v))if len(v)>1 else 0}

base=[read(s,a.base)for s in range(a.end)]
bm=json.loads((RUNS/a.base/'metrics.json').read_text())['cases']
out=[]
for run in a.candidates:
    cm=json.loads((RUNS/run/'metrics.json').read_text())['cases'];rows=[]
    for seed,(bc,bp)in enumerate(base):
        cc,cp=read(seed,run)
        flips=sum((x[1]>x[0])!=(y[1]>y[0])for x,y in zip(bc,cc))
        row={'seed':seed,'flips':flips,'max_probability_change':max(abs(x-y)for x,y in zip(bp,cp)),
             'score_delta':100*math.log(cm[str(seed)]['score']/bm[str(seed)]['score'])}
        rows.append(row)
    groups={}
    for key,selected in [('no_flip',[r for r in rows if not r['flips']]),
                         ('flip',[r for r in rows if r['flips']]),
                         ('probability_change_below_01',[r for r in rows if r['max_probability_change']<.1])]:
        groups[key]=stats([r['score_delta']for r in selected])
    result={'run':run,'flips':stats([r['flips']for r in rows]),'groups':groups,'rows':rows}
    print(run,result['flips'],groups)
    out.append(result)
(HERE/a.output).write_text(json.dumps(out,indent=2)+'\n')
