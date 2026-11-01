#!/usr/bin/env python3
"""measure.py の生データを小さな CSV / JSON に集約する。stdout は別途全バイト比較済み。"""
import csv
import json
from pathlib import Path
import statistics

HERE = Path(__file__).resolve().parent
experiments = []
all_rows = []
for path in sorted((HERE / 'data').glob('*/results.json')):
    data = json.loads(path.read_text())
    rows = data['records']
    summary = {'label': path.parent.name, 'counts': data['counts'], 'binaries': {}}
    for binary in dict.fromkeys(row['binary'] for row in rows):
        group = [row for row in rows if row['binary'] == binary]
        summary['binaries'][binary] = {
            'n': len(group), 'seeds': sorted(set(row['seed'] for row in group)),
            'map_median': statistics.median(row['metrics']['map_end_sec'] for row in group),
            'anneal_median': statistics.median(row['metrics']['anneal_end_sec']-row['metrics']['map_end_sec'] for row in group),
        }
    experiments.append(summary)
    for row in rows:
        m = row['metrics']
        all_rows.append({'label': path.parent.name, 'binary': row['binary'], 'seed': row['seed'], 'repeat': row['repeat'],
                         'map_sec': m['map_end_sec'], 'anneal_sec': m['anneal_end_sec']-m['map_end_sec'],
                         'climb_sec': m['climb_end_sec']-m['anneal_end_sec'], 'req_sec':m['req_sec'],
                         'score':int(m['Score']), 'fast_requests':int(m['fast_requests']), 'helper_papers':int(m['helper_papers']),
                         'stdout_bytes':row['bytes'], 'sha256':row['sha256']})
if not all_rows:
    raise SystemExit('data/ に計測記録がありません。measure.py を実行してください。保存済みの要約は変更しません。')
# Preserve evidence for runs whose bulky raw outputs have already been cleaned up.
labels = {e['label'] for e in experiments}
old_path = HERE / 'experiments-summary.json'
if old_path.exists():
    experiments = [e for e in json.loads(old_path.read_text()) if e['label'] not in labels] + experiments
old_csv = HERE / 'measurements.csv'
if old_csv.exists():
    with old_csv.open() as f:
        old_rows = list(csv.DictReader(f))
    for row in old_rows:
        for key in ('seed','repeat','score','fast_requests','helper_papers','stdout_bytes'):
            row[key] = int(row[key])
        for key in ('map_sec','anneal_sec','climb_sec','req_sec'):
            row[key] = float(row[key])
    all_rows = [r for r in old_rows if r['label'] not in labels] + all_rows
(HERE / 'experiments-summary.json').write_text(json.dumps(experiments,indent=2)+'\n')
with (HERE / 'measurements.csv').open('w') as f:
    w=csv.DictWriter(f,fieldnames=list(all_rows[0])); w.writeheader(); w.writerows(all_rows)

final = {}
raw_speed = []
for label, field in [('final-anneal-speed','anneal_sec'),('final-map-speed','map_sec')]:
    rows = [r for r in all_rows if r['label']==label]
    if not rows: continue
    for seed, repeat in sorted(set((r['seed'],r['repeat']) for r in rows)):
        pair = {r['binary']:r[field] for r in rows if r['seed']==seed and r['repeat']==repeat}
        raw_speed.append({'phase':label,'seed':seed,'repeat':repeat+1,'base_sec':pair['base'],'main_sec':pair['main'],'main_over_base':pair['main']/pair['base']})
    records = []
    for seed in sorted(set(row['seed'] for row in rows)):
        group = [row for row in rows if row['seed']==seed]
        base=[r[field] for r in group if r['binary']=='base']; main=[r[field] for r in group if r['binary']=='main']
        records.append({'seed':seed,'base_median':statistics.median(base),'main_median':statistics.median(main),'speedup':statistics.median(base)/statistics.median(main)})
    base=[r[field] for r in rows if r['binary']=='base']; main=[r[field] for r in rows if r['binary']=='main']
    final[label] = {'counts': next(e['counts'] for e in experiments if e['label']==label),
                    'pairs':len(base),'base_median':statistics.median(base),'main_median':statistics.median(main),
                    'speedup':statistics.median(base)/statistics.median(main),
                    'paired_ratio_median':statistics.median(b/a for a,b in zip(base,main)), 'by_seed':records}
with (HERE / 'speed-raw.csv').open('w') as f:
    if raw_speed:
        w=csv.DictWriter(f,fieldnames=list(raw_speed[0])); w.writeheader(); w.writerows(raw_speed)
(HERE / 'speed-summary.json').write_text(json.dumps(final,indent=2)+'\n')

checks_path = HERE / 'equality-summary.json'
checks = json.loads(checks_path.read_text()) if checks_path.exists() else {}
for label in ['final-equal','final-trace','final-clang','modes-g32','modes-g28']:
    path=HERE/'data'/label/'results.json'
    if not path.exists(): continue
    rows=json.loads(path.read_text())['records']; groups=[]
    for seed in sorted(set(row['seed'] for row in rows)):
        group=[row for row in rows if row['seed']==seed]
        a,b=group
        metrics=['Score','anneal_iters','G','fast_requests','helper_papers']
        metrics += [k for k in a['metrics'] if 'trace_' in k]
        assert a['sha256']==b['sha256'] and a['bytes']==b['bytes']
        assert all(a['metrics'][k]==b['metrics'][k] for k in metrics)
        groups.append({'seed':seed,'bytes':a['bytes'],'sha256':a['sha256'],
                       **{k:a['metrics'][k] for k in metrics}})
    checks[label]={'cases':len(groups),'all_equal':True,'records':groups}
(HERE / 'equality-summary.json').write_text(json.dumps(checks,indent=2)+'\n')

path=HERE/'data'/'final-profile-sampled'/'results.json'
if path.exists():
    data=json.loads(path.read_text()); rows=data['records']; output={}
    for binary in ('profile-base','profile-main'):
        group=[r['metrics'] for r in rows if r['binary']==binary]
        output[binary]={'n':len(group),'anneal_sec':statistics.median(m['anneal_end_sec']-m['map_end_sec'] for m in group),
                        'assign_sec':statistics.median(m['assign_sec'] for m in group)}
        for i in range(7):
            output[binary][f'move_{i}_sec']=statistics.median((m['anneal_end_sec']-m['map_end_sec'])*m[f'cycles_{i}']*m['profile_stride']/m['anneal_total_ticks'] for m in group)
            output[binary][f'move_{i}_share']=statistics.median(m[f'cycles_{i}']*m['profile_stride']/m['anneal_total_ticks'] for m in group)
        for label in ['propose','match','apply']:
            output[binary][f'map_{label}_sec']=statistics.median(m['assign_sec']*m[f'map_{label}_ticks']/m['map_total_ticks'] for m in group)
            output[binary][f'map_{label}_share']=statistics.median(m[f'map_{label}_ticks']/m['map_total_ticks'] for m in group)
    (HERE/'profile-summary.json').write_text(json.dumps(output,indent=2)+'\n')
    (HERE/'profile-raw.json').write_text(json.dumps({'counts':data['counts'],'records':[{'binary':r['binary'],'seed':r['seed'],'repeat':r['repeat'],'metrics':r['metrics']} for r in rows]},indent=2)+'\n')
print(json.dumps(final,indent=2))
