"""Choose from a predeclared priority using final timing alone, before held-out replay."""
from pathlib import Path
import json,sys,datetime
P=Path(__file__).resolve().parent;root=P.parents[1];R=Path('/home/sato/ahc074/runs')
out=root/'solutions'/sys.argv[1];config=json.loads((out/'FROZEN.json').read_text());normal=sys.argv[2:]
def mean(v):return sum(v)/len(v)
def p99(v):v=sorted(v);i=.99*(len(v)-1);lo=int(i);return v[lo]+(i-lo)*(v[lo+1]-v[lo])
result={}
for run in normal:
    meta=json.loads((R/run/'meta.json').read_text());assert meta['status']=='ok'
    load=meta.get('outside_load') or {}
    assert load.get('mean_cores',0)<=.5 and load.get('max_cores',0)<=3,('outside load requires timing repeat',run,load)
    rows=json.loads((R/run/'metrics.json').read_text())['cases'];assert len(rows)==2000
    ts=[]
    for row in rows.values():
        x=row['stderr'];ts.append(1.04*x['helper_end_sec']+1.35*x['req_sec']+x['end_sec']-x['helper_end_sec']-x['req_sec'])
    result[run]={'mean':mean(ts),'p99':p99(ts),'max':max(ts)}
old=next(r for r in normal if r.endswith('_argon-des-perf-latew105'))
nofb=next(r for r in normal if r.endswith('_deval-vbranch-nofb'))
chosen=None
for name in config['priority']:
    run=next(r for r in normal if r.endswith('_'+name));z=result[run]
    z['ratio_old']=z['mean']/result[old]['mean']
    z['eligible']=z['ratio_old']<=1.10 and z['p99']<=result[nofb]['p99']
    if chosen is None and z['eligible']:chosen=name
answer={'priority':config['priority'],'chosen':chosen,'normal':normal,'timing':result,
        'time':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat(),
        'selection_used_scores':False,'held_out_replay_not_started':True}
(out/'time-selection.json').write_text(json.dumps(answer,indent=2)+'\n');print(json.dumps(answer,indent=2))
