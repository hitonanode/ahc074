"""Post-hoc diagnostic thresholds; these results do not select a submitted policy."""
import json, math, statistics
from pathlib import Path

here=Path(__file__).resolve().parent
data=json.loads((here/'steady-500.json').read_text())
root=Path('/home/sato/ahc074/runs')
base=json.loads((root/data[0]['run']/'metrics.json').read_text())['cases']
cand=json.loads((root/data[1]['run']/'metrics.json').read_text())['cases']
rows=[]
for threshold in [0, 1e-6, 1e-5, 1e-4, 3e-4, 1e-3, 3e-3]:
    vals=[];count=0
    for seed,row in cand.items():
        use=row['stderr']['d1_steady_best_delta'] < -threshold
        count+=use
        vals.append(100*math.log(row['score']/base[seed]['score']) if use else 0)
    rows.append(dict(threshold=threshold,count=count,mean=statistics.mean(vals),
                     se=statistics.stdev(vals)/math.sqrt(len(vals))))
(here/'thresholds.json').write_text(json.dumps(rows,indent=2)+'\n')
for row in data:
    print(row['run'],'score',row['score'],'W/T/L',row['wins'],row['ties'],row['losses'],'judge',row['judge'])
    for name in ['req_sec','helper_end_sec','d1_steady_best_delta','d1_sec','self_wrong','op_label_errors']:
        print(name,row['metrics'].get(name))
print('diagnostic thresholds',json.dumps(rows))
