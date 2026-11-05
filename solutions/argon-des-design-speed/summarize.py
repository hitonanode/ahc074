"""Read cached metrics and saved outputs; launch with whenidle.sh."""
import argparse, collections, json, math, statistics
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=Path('/home/sato/ahc074/runs')
def stats(v):
    return dict(mean=statistics.mean(v),se=statistics.stdev(v)/math.sqrt(len(v))if len(v)>1 else 0,
                min=min(v),max=max(v))
def percentile(v,p):
    v=sorted(v);x=(len(v)-1)*p;i=int(x);return v[i]+(v[min(i+1,len(v)-1)]-v[i])*(x-i)
p=argparse.ArgumentParser();p.add_argument('runs',nargs='+');p.add_argument('--output',default='summary.json');p.add_argument('--end',type=int);a=p.parse_args()
base=None;results=[]
for name in a.runs:
    cases=json.loads((ROOT/name/'metrics.json').read_text())['cases']
    if a.end is not None:cases={s:c for s,c in cases.items()if int(s)<a.end}
    for c in cases.values():
        e=c['stderr'];last=0
        for phase in ['map','anneal','climb','match','perforation','helper']:
            now=e[phase+'_end_sec'];e['phase_'+phase+'_sec']=now-last;last=now
    if base is None:base=cases
    keys=set.intersection(*(set(row['stderr'])for row in cases.values()))
    row=dict(run=name,n=len(cases),wa=sum(not c['score']for c in cases.values()),metrics={},deltas={})
    row['score']=stats([100*math.log(c['score']/base[s]['score'])for s,c in cases.items()if c['score']and base[s]['score']])
    row['wtl']=[sum(c['score']<base[s]['score']for s,c in cases.items()),sum(c['score']==base[s]['score']for s,c in cases.items()),sum(c['score']>base[s]['score']for s,c in cases.items())]
    for k in sorted(keys):
        if k.startswith(('d2_','model_','perforation_','perf_','phase_')) or k in ['req_sec','helper_end_sec','end_sec','self_wrong','op_label_errors','gobj_after','proxy_after']:
            row['metrics'][k]=stats([c['stderr'][k]for c in cases.values()])
            row['deltas'][k]=stats([c['stderr'][k]-base[s]['stderr'][k]for s,c in cases.items()])
    judge=[c['stderr']['end_sec']+.04*c['stderr']['helper_end_sec']+.35*c['stderr']['req_sec']for c in cases.values()]
    row['judge']={**stats(judge),'p99':percentile(judge,.99),'over2':sum(x>2 for x in judge)}
    base_judge=[base[s]['stderr']['end_sec']+.04*base[s]['stderr']['helper_end_sec']+.35*base[s]['stderr']['req_sec']for s in cases]
    row['judge_delta']=stats([x-y for x,y in zip(judge,base_judge)])
    row['judge_delta']['p99_difference']=percentile(judge,.99)-percentile(base_judge,.99)
    print(name,'score',row['score'],'W/T/L',row['wtl'],'judge',row['judge'])
    print('judge_delta',row['judge_delta'])
    for k,v in row['metrics'].items():print(k,v)
    print('deltas',row['deltas'])
    results.append(row)
(HERE/a.output).write_text(json.dumps(results,indent=2)+'\n')
