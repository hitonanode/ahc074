"""Small, single-core score-only diagnostic of the four shared-prefix branches."""
from pathlib import Path
import json,math,statistics
HERE=Path(__file__).resolve().parent
RUNS=Path('/home/sato/ahc074/runs')
manifest={r['tag']:r for r in map(json.loads,(HERE/'experiments.jsonl').read_text().splitlines())}
def load(run):
    return {int(c['seed']):c['order_scores'] for c in json.loads((RUNS/run/'result.json').read_text())['cases']}
base=load('20261107-015743_deval-seed')
sets=[load(manifest[f'trainbranch{i}']['replay']) for i in range(4)]
def correlation(a,b):
    aa=statistics.mean(a);bb=statistics.mean(b)
    return sum((x-aa)*(y-bb) for x,y in zip(a,b))/math.sqrt(sum((x-aa)**2 for x in a)*sum((y-bb)**2 for y in b))
def summary(a):return [statistics.mean(a),statistics.stdev(a)/len(a)**.5]
halves=[[],[]];var=[];oracle=[];random=[]
for seed in range(500):
    y=[sets[i][seed] for i in range(4)]
    for half in range(2):
        means=[statistics.mean(row[4*half:4*half+4]) for row in y]
        avg=statistics.mean(means);halves[half].extend(x-avg for x in means)
    means=[statistics.mean(row) for row in y];var.append(statistics.variance(means)/1024**2)
    chosen=min(range(4),key=lambda i:statistics.mean(y[i][:4]))
    oracle.append(100*math.log(statistics.mean(y[chosen][4:])/statistics.mean(base[seed][4:])))
    random.append(100*math.log(statistics.mean(statistics.mean(row[1:]) for row in y)/statistics.mean(base[seed][1:])))
r=correlation(*halves);reliability=2*r/(1+r)
out=dict(n=500,half_correlation=r,reliability=reliability,design_sd=math.sqrt(statistics.mean(var)*reliability),
         oracle_4_4=summary(oracle),random_against_base=summary(random))
(HERE/'branch_oracle.json').write_text(json.dumps(out,indent=2));print(out)
