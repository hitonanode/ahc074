"""Compare final late-stage objectives to realized moves, using saved metrics only."""
import argparse
import json
import math
import statistics
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUNS = Path('/home/sato/ahc074/runs')
p = argparse.ArgumentParser()
p.add_argument('runs', nargs='+')
p.add_argument('--output', default='diagnosis.json')
a = p.parse_args()

def read(run):
    obj = json.loads((RUNS/run/'metrics.json').read_text())
    return {int(k): v for k, v in obj['cases'].items()}

def stats(values):
    return {'mean': statistics.mean(values),
            'se': statistics.stdev(values)/math.sqrt(len(values)) if len(values)>1 else 0}

def corr(x,y):
    return statistics.correlation(x,y) if statistics.pstdev(x)*statistics.pstdev(y) else 0

base = read(a.runs[0])
results=[]
for run in a.runs[1:]:
    rows = read(run)
    weight = int(run.rsplit('latew',1)[1])/100 if 'latew' in run else .5 if run.endswith('wholehalf') else 1.
    pred=[]; actual=[]; changed=0; examples=[]
    for seed,c in rows.items():
        b=base[seed]; x=c['stderr']; y=b['stderr']
        if 'd2_whole_model_final' in x:
            dv=x['d2_whole_model_final']-x['d2_whole_model_initial']-weight*(x['d2_whole_filler_final']-x['d2_whole_filler_initial'])
        elif 'd2_restore_cost' in x:
            dv=x['d2_restore_cost']-.7*(x['d2_restore_owner']+x['d2_restore_donor'])
        else:
            dv=x['d2_model_final']-y['d2_model_final']-weight*(x['d2_filler_final']-y['d2_filler_final'])
        da=(c['score']-b['score'])/1024
        pred.append(dv);actual.append(da)
        changed+= c['score']!=b['score']
        examples.append({'seed':seed,'predicted':dv,'actual':da})
    row={'run':run,'n':len(rows),'weight':weight,'changed_scores':changed,
         'predicted_moves':stats(pred),'actual_moves':stats(actual),'correlation':corr(pred,actual),
         'worst':sorted(examples,key=lambda z:z['actual'],reverse=True)[:8],
         'best':sorted(examples,key=lambda z:z['actual'])[:8]}
    print(run, {k:v for k,v in row.items() if k not in ['worst','best']})
    results.append(row)
(HERE/a.output).write_text(json.dumps(results,indent=2)+'\n')
