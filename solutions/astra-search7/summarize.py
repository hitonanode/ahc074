#!/usr/bin/env python3
"""保存済みCSV/JSONから実験一覧と最終検証値を再集計する。解法は実行しない。"""
from pathlib import Path
import csv,json,statistics,math
h=Path(__file__).resolve().parent
experiments=[]
for p in h.glob('*.json'):
 d=json.loads(p.read_text())
 if 'compare' in d and 'config' in d:
  experiments.append((p.stem,d))
experiments.sort(key=lambda x:min(float(r['started']) for r in csv.DictReader((h/(x[0]+'.csv')).open())))
lines=['# 実験一覧','','差はケースごとの100 log(候補/基準)の平均 ± SE。負が改善。',
       '通常比較は基準8個＋候補8個を交互起動する。固定回数の診断は性能の採否に使わない。','',
       '| 比較 | seed | 件数 | 差 ± SE (%) | 勝/分/敗 | 候補end_sec最大 |',
       '|---|---|---:|---:|---:|---:|']
for name,d in experiments:
 c=d['compare']['gobj_after'];v=d['variants'][d['config']['candidate']]
 suffix=' 固定回数' if d['config']['fixed'] else ''
 lines.append(f"| [{name}]({name}.csv){suffix} | {d['config']['seeds']} | {c['n']} | {c['log_pct']:+.4f} ± {c['se_pct']:.4f} | {c['win']}/{c['tie']}/{c['loss']} | {v['end_sec']['max']:.5f} |")
(h/'EXPERIMENTS.md').write_text('\n'.join(lines)+'\n')
selection=json.loads((h/'selection-summary.json').read_text());final={};validation={}
for dst,src,chosen,hold in [('main','sources2','sources2-confirm','holdout-main'),('cand2/main','temp10','temp10-confirm','holdout-cand2')]:
 sel=json.loads((h/(chosen+'.json')).read_text());ho=json.loads((h/(hold+'.json')).read_text())
 labels=selection[src]['labels']+[hold]
 rows=[]
 for label in labels:
  d=json.loads((h/(label+'.json')).read_text());cand=d['config']['candidate']
  rows += [r for r in csv.DictReader((h/(label+'.csv')).open()) if r['binary']==cand]
 final[dst]={'selection_all_repetitions':{k:v for k,v in selection[src].items() if k!='paired_mean_by_seed'},
             'selection_last':sel['compare']['gobj_after'],'holdout':ho['compare']['gobj_after'],
             'normal_candidate_runs':len(rows),'distinct_seeds':len({r['seed'] for r in rows}),
             'end_sec_max':max(float(r['end_sec']) for r in rows),
             'selection_last_means':{b:d['gobj_after']['mean'] for b,d in sel['variants'].items()},
             'holdout_means':{b:d['gobj_after']['mean'] for b,d in ho['variants'].items()}}
 validation[dst]={'runs':len(rows),'wa':sum(float(r['Score'])<=0 or int(r['returncode'])!=0 for r in rows),
                  'end_sec_above_1_75':sum(float(r['end_sec'])>1.75 for r in rows),
                  'self_wrong_sum':sum(float(r['self_wrong']) for r in rows),
                  'fast_requests_sum':sum(float(r['fast_requests']) for r in rows),
                  'G_values':sorted({float(r['G']) for r in rows}),
                  'cap_window_values':sorted({float(r['cap_window']) for r in rows}),
                  'plan_failures_sum':sum(float(r['plan_failures']) for r in rows)}
for label in ['verify-sources2-fixed','clang-main-fixed','clang-cand2-fixed','direct-fixed']:
 d=json.loads((h/(label+'.json')).read_text());rows=list(csv.DictReader((h/(label+'.csv')).open()))
 base={r['seed']:r for r in rows if r['binary']==d['config']['base']}
 cand=[r for r in rows if r['binary']==d['config']['candidate']]
 validation[label]={k:sum(float(r[k])==float(base[r['seed']][k]) for r in cand) for k in ['gobj_after','search_exact_evals','total_moves','Score']}
 validation[label]['n']=len(cand)
 validation[label]['verify_counts']={k:int(sum(float(r[k]) for r in cand)) for k in cand[0] if k.startswith('verify_')}
normal=[(name,d) for name,d in experiments if not d['config']['fixed']]
validation['all_normal']={'comparisons':len(normal),'executions':sum(2*d['compare']['gobj_after']['n'] for _,d in normal),
 'max_end_sec':max(v['end_sec']['max'] for _,d in normal for v in d['variants'].values()),
 'wa':0}
for label,d in normal:
 for r in csv.DictReader((h/(label+'.csv')).open()):
  validation['all_normal']['wa']+=float(r['Score'])<=0 or int(r['returncode'])!=0
(h/'final-summary.json').write_text(json.dumps(final,indent=2)+'\n')
(h/'validation-summary.json').write_text(json.dumps(validation,indent=2)+'\n')
print(json.dumps(final,indent=2));print(json.dumps(validation,indent=2))
