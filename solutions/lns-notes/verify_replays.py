"""Audit all frozen replay lists for wrong displays and planner failures.

Invoke under flock + nice. Read only diagnostic tails where possible; the solver
is never executed by this script.
"""
from pathlib import Path
import json,re

h=Path(__file__).resolve().parent;r=Path('/home/sato/ahc074/runs')
records=json.loads((h/'heldout-runs.json').read_text());assert len(records)==3
runs=['20261108-070629_deval-helper-wide']+[x for row in records for x in row['replays']]
keys=['self_wrong','op_label_errors','plan_failures','unsafe_plans']
patterns={k:re.compile(rb'^'+k.encode()+rb' = ([-+0-9.eE]+)$',re.M) for k in keys}
out={}
for rid in runs:
    d=r/rid;m=json.loads((d/'meta.json').read_text());assert m['status']=='ok'
    cs=json.loads((d/'result.json').read_text())['cases'];assert len(cs)==500
    count=0
    for c in cs:
        assert len(c['order_scores'])==8 and min(c['order_scores'])>0
        for j,score in enumerate(c['order_scores']):
            p=(d if j==0 else d/f'orders/{j}')/f'err/{c["seed"]:04d}.txt'
            with p.open('rb') as f:
                f.seek(0,2);f.seek(max(0,f.tell()-32768));t=f.read()
            values={k:pat.findall(t) for k,pat in patterns.items()}
            if not all(values.values()):
                t=p.read_bytes();values={k:pat.findall(t) for k,pat in patterns.items()}
            for k,v in values.items():assert v and float(v[-1])==0,(p,k,v)
            actual=re.findall(rb'^Score = ([0-9]+)$',t,re.M)
            assert actual and int(actual[-1])==score,(p,score,actual)
            count+=1
    out[rid]={'case_lists':count,'requests':count*1024,'all_counters_zero':True,'tester_scores_match':True}
(h/'final-replay-audit.json').write_text(json.dumps(out,indent=2)+'\n')
print('All frozen replays passed:',sum(x['case_lists'] for x in out.values()),'case-lists')
