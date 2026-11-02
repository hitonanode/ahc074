#!/usr/bin/env python3
"""Export immutable per-seed comparison data and paired standard errors from pahcer runs."""
import argparse
import csv
import hashlib
import json
import math
import pathlib
import re
import statistics

ROOT = pathlib.Path(__file__).resolve().parents[2]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--label', required=True)
p.add_argument('--out', type=pathlib.Path, default=pathlib.Path(__file__).parent/'results')
p.add_argument('runs', nargs='+')
a = p.parse_args()
a.out.mkdir(parents=True, exist_ok=True)
rows, summaries = [], []
baseline = None
for run_id in a.runs:
    path = ROOT / 'runs' / run_id
    result = json.loads((path/'result.json').read_text())
    meta = json.loads((path/'meta.json').read_text())
    replay_path = path/'metrics.json'
    replay_cases = json.loads(replay_path.read_text()).get('cases', {}) if replay_path.exists() else {}
    arm_rows = []
    for case in result['cases']:
        seed = int(case['seed'])
        errpath = path/'err'/f'{seed:04d}.txt'
        metrics = {k:float(v) for k,v in re.findall(r'^\s*([A-Za-z_0-9]+)\s*=\s*([-+.0-9eE]+)\s*$',errpath.read_text(),re.M)}
        row = {'run_id':run_id,'seed':seed,'score':case['score'],'execution_time':case['execution_time']}
        for k,v in metrics.items():
            if k != 'Score': row[k] = v
        arm_rows.append(row)
    if baseline is None:
        baseline = {row['seed']:row for row in arm_rows}
    paired = [(row,baseline[row['seed']]) for row in arm_rows if row['seed'] in baseline
              and row['score']>0 and baseline[row['seed']]['score']>0]
    deltas = [100*math.log(x['score']/y['score']) for x,y in paired]
    metric_keys = sorted(set(k for row in arm_rows for k,v in row.items() if isinstance(v,(float,int))) - {'seed'})
    summaries.append({'run_id':run_id,'case_count':len(arm_rows),'valid_pairs':len(paired),
        'wa_count':sum(row['score']==0 for row in arm_rows),
        'over_2s':sum(row['execution_time']>2 for row in arm_rows),
        'mean_log_percent':statistics.mean(deltas) if deltas else None,
        'se_log_percent':statistics.stdev(deltas)/math.sqrt(len(deltas)) if len(deltas)>1 else None,
        'win_tie_loss':[sum(x['score']<y['score'] for x,y in paired),sum(x['score']==y['score'] for x,y in paired),sum(x['score']>y['score'] for x,y in paired)],
        'metrics':{k:{'n':sum(k in row for row in arm_rows),'mean':statistics.mean(row[k] for row in arm_rows if k in row),
                      'min':min(row[k] for row in arm_rows if k in row),
                      'max':max(row[k] for row in arm_rows if k in row)} for k in metric_keys},
        'source_sha256':hashlib.sha256((path/'src/main.cpp').read_bytes()).hexdigest(),
        'compile_command':meta['compile_command'],'comment':meta['comment'],
        'replayed_cases':len(replay_cases),
        'replay_error_cases':sum(bool(c.get('error')) for c in replay_cases.values()),
        'replay_mean_E':statistics.mean(c['E'] for c in replay_cases.values()) if replay_cases else None,
        'replay_mismatch':meta['summary'].get('replay_mismatch')})
    rows.extend(arm_rows)
columns = list(dict.fromkeys(k for row in rows for k in row))
with (a.out/(a.label+'.csv')).open('w') as f:
    w=csv.DictWriter(f,fieldnames=columns);w.writeheader();w.writerows(rows)
(a.out/(a.label+'.json')).write_text(json.dumps(summaries,indent=2)+'\n')
for s in summaries:
    print(s['run_id'],s['case_count'],round(s['metrics']['score']['mean']/1024,6),
          s['mean_log_percent'],s['se_log_percent'],s['win_tie_loss'],'WA',s['wa_count'],'>2s',s['over_2s'])
