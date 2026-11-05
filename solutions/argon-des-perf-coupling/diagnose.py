"""Saved metrics only. Run through whenidle and exclusive runs/.lock."""
import collections, json, math, statistics
from pathlib import Path
ROOT=Path('/home/sato/ahc074/runs'); HERE=Path(__file__).resolve().parent
def stats(x):
    return dict(mean=statistics.mean(x), se=statistics.stdev(x)/math.sqrt(len(x)), min=min(x), max=max(x))
def corr(x,y):
    return statistics.correlation(x,y) if statistics.pstdev(x)*statistics.pstdev(y) else 0
names=['20261106-065002_argon-des-perf-modelprobe','20261106-065003_argon-des-perf-modelprobe']
old=['20261106-062233_argon-des-perf-rematch-v2','20261106-062412_argon-des-perf-whole']
rows=[json.loads((ROOT/n/'metrics.json').read_text())['cases']for n in names]
previous=[json.loads((ROOT/n/'metrics.json').read_text())['cases']for n in old]
seeds=sorted(set.intersection(*(set(x)for x in rows)))
result=dict(runs=names,previous=old,n=len(seeds),metrics={},prediction={},labels={})
actual=[(rows[1][s]['score']-rows[0][s]['score'])/1024 for s in seeds]
result['actual']=stats(actual)
result['identical_scores']=[sum(r[s]['score']==p[s]['score']for s in seeds)for r,p in zip(rows,previous)]
keys=sorted(k for k in rows[0][seeds[0]]['stderr'] if k.startswith('d2_probe_'))
for k in keys:
    v=[[r[s]['stderr'][k] for s in seeds]for r in rows]
    d=[b-a for a,b in zip(*v)]
    result['metrics'][k]=dict(base=stats(v[0]),candidate=stats(v[1]),delta=stats(d),corr=corr(d,actual))
for model in ['sum','interval','unrestricted','one']:
    delta=[(rows[1][s]['stderr']['d2_probe_hole']-rows[0][s]['stderr']['d2_probe_hole'])-(rows[1][s]['stderr']['d2_probe_'+model]-rows[0][s]['stderr']['d2_probe_'+model])for s in seeds]
    result['prediction'][model]=dict(**stats(delta),corr=corr(delta,actual))
for name in old:
    counts=collections.Counter()
    for s in seeds:
        for line in (ROOT/name/'err'/f'{int(s):04d}.txt').read_text().splitlines():
            if line.startswith('@ops '):
                for token in line.split('=',1)[1].split():
                    label, sep, count=token.partition('*');counts[label]+=int(count)if sep else 1
    result['labels'][name]={k:v/(len(seeds)*1024)for k,v in sorted(counts.items())}
result['label_delta']={k:result['labels'][old[1]].get(k,0)-result['labels'][old[0]].get(k,0)for k in set.union(*(set(v)for v in result['labels'].values()))}
(HERE/'whole-diagnosis.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
