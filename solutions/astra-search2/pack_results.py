#!/usr/bin/env python3
"""探索中の比較を小さなCSVと要約JSONに集約する（元ファイルは削除しない）。"""
import csv,json,pathlib
h=pathlib.Path(__file__).resolve().parent
summary=json.loads((h/'experiments-summary.json').read_text()) if (h/'experiments-summary.json').exists() else {}
rows=list(csv.DictReader((h/'experiments.csv').open())) if (h/'experiments.csv').exists() else []
fields=['label','binary','seed','rep','cpu','gobj_before','gobj_after','sim_moves','sim_wrong','total_moves','self_wrong','end_sec','map_iters','gopt_steps','search_accept','search_exact_evals','search_memo_hits','forced_steps','climb_forced_steps','tabu_skips','direct_steps','repair_tried','repair_found','repair_accepted','rescue_checks','rescued','double_tried','double_accepted','guide_repaired','weighted_rescued','weighted_rejected']
for p in sorted(h.glob('*.json')):
 if p.stem.startswith(('final-','holdout-')) or p.name in ['experiments-summary.json','build-info.json','scope-summary.json','validation-summary.json']: continue
 data=json.loads(p.read_text())
 if 'compare' not in data or not (h/(p.stem+'.csv')).exists(): continue
 summary[p.stem]=data
 rows=[r for r in rows if r['label']!=p.stem]
 for r in csv.DictReader((h/(p.stem+'.csv')).open()):
  rows.append(dict(label=p.stem,**{k:r[k] for k in fields[1:] if k in r}))
(h/'experiments-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
with (h/'experiments.csv').open('w') as f:
 w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
print(f'{len(summary)} experiments, {len(rows)} rows')
