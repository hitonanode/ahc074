"""Reproduce final metrics from completed saved runs. Execute under the shared flock."""
from pathlib import Path
import sys,json,hashlib
import numpy as np
from analyze_quality import compare
S=Path(sys.argv[1]);R=Path('/home/sato/ahc074/runs')
eval=json.loads((S/'final-evaluation.json').read_text());runs=eval['normal']
assert len(runs)==3
scores={};timing={};meta={};summary={}
for run in runs:
 p=R/run;meta[run]=json.loads((p/'meta.json').read_text());assert meta[run]['status']=='ok'
 cases=json.loads((p/'result.json').read_text())['cases'];assert len(cases)==2000
 scores[run]={int(c['seed']):float(c['score']) for c in cases};assert sorted(scores[run])==list(range(2000))
 assert min(scores[run].values())>0
 m=json.loads((p/'metrics.json').read_text())['cases'];assert len(m)==2000
 vals=[m[str(i)]['stderr'] for i in range(2000)]
 end=np.array([v['end_sec'] for v in vals]);des=np.array([v['helper_end_sec'] for v in vals]);req=np.array([v['req_sec'] for v in vals])
 judge=1.04*des+1.35*req+(end-des-req);real=np.array([c['execution_time'] for c in cases])
 timing[run]=judge
 def distribution(x):return {'mean':float(x.mean()),'p50':float(np.quantile(x,.5)),'p95':float(np.quantile(x,.95)),'p99':float(np.quantile(x,.99)),'p999':float(np.quantile(x,.999)),'max':float(x.max()),'over_1.8':int((x>1.8).sum()),'over_1.9':int((x>1.9).sum()),'over_2.0':int((x>2).sum())}
 summary[run]={'mean_score':float(np.mean(list(scores[run].values()))),'E':float(np.mean([m[str(i)]['E'] for i in range(2000)])),'WA':0,'judge':distribution(judge),'end_sec':distribution(end),'execution_time':distribution(real),'design_mean':float(des.mean()),'req_mean':float(req.mean()),'outside_load':meta[run].get('outside_load',{})}
 summary[run]['score_comparisons']={}
for run in runs:
 for ref in runs[:2]:
  d=np.array([100*np.log(scores[run][i]/scores[ref][i]) for i in range(2000)])
  dt=timing[run]-timing[ref]
  summary[run]['score_comparisons'][ref]={'mean':float(d.mean()),'se':float(d.std(ddof=1)/np.sqrt(2000)),'wtl':[int((d<0).sum()),int((d==0).sum()),int((d>0).sum())]}
  summary[run].setdefault('time_comparisons',{})[ref]={'ratio':float(timing[run].mean()/timing[ref].mean()),'delta':float(dt.mean()),'se':float(dt.std(ddof=1)/np.sqrt(2000))}
quality=compare(eval['baseline_replay'],eval['candidate_replay'],(500,1000));assert quality['n']==500
for run in [eval['baseline_replay'],eval['candidate_replay']]:
 cases=json.loads((R/run/'result.json').read_text())['cases'];assert len(cases)==500
 assert all(len(c['order_scores'])==8 and min(c['order_scores'])>0 for c in cases)
source=(S/'main.cpp').read_bytes();assert hashlib.sha256(source).hexdigest()==eval['freeze']['sha256']
last=summary[runs[-1]];ref=summary[runs[1]]
verdict={'judge_mean_within_limit':last['time_comparisons'][runs[0]]['ratio']<=1.10,'judge_p99_within_limit':last['judge']['p99']<=ref['judge']['p99'],'gain_at_least_point_one':quality['results']['fresh']['mean']<=-.10,'normal_clear_improvement':last['score_comparisons'][runs[1]]['mean']+2*last['score_comparisons'][runs[1]]['se']<0}
out={'normal':summary,'replay':quality,'source_bytes':len(source),'source_sha256':hashlib.sha256(source).hexdigest(),'verdict':verdict}
(S/'final-metrics.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
lines=['## 最終の通常2000ケース比較','',
'同じ `--compare` のseed 0–1999、24並列。ケースごとのlogスコア比を平均した。負が改善、±はケース間の標準誤差。最終通常比較はpahcerへ記録した。','',
'| 解法 | 平均スコア | 旧SOTA比 ± SE | W/T/L | nofb比 ± SE | W/T/L |','|---|---:|---:|---:|---:|---:|']
for run in runs:
 d=summary[run];a=d['score_comparisons'][runs[0]];b=d['score_comparisons'][runs[1]]
 lines.append(f"| {run.split('_',1)[1]} | {d['mean_score']:.2f} | {a['mean']:+.4f} ± {a['se']:.4f}% | {'/'.join(map(str,a['wtl']))} | {b['mean']:+.4f} ± {b['se']:.4f}% | {'/'.join(map(str,b['wtl']))} |")
lines+=['','WAは全解法0。平均E: '+', '.join(f"{r.split('_',1)[1]} {summary[r]['E']:.6f}" for r in runs)+'。','',
'judge-modelは `1.04 × helper_end_sec + 1.35 × req_sec + (end_sec − helper_end_sec − req_sec)`。時間の判断には、この通常同時比較だけを使う。','',
'| 解法 | judge平均 | 旧SOTA比 | nofb比 | judge p99 | judge最大 | 設計平均 | 注文平均 |','|---|---:|---:|---:|---:|---:|---:|---:|']
for run in runs:
 d=summary[run];j=d['judge'];lines.append(f"| {run.split('_',1)[1]} | {j['mean']:.4f} s | {d['time_comparisons'][runs[0]]['ratio']:.4f} | {d['time_comparisons'][runs[1]]['ratio']:.4f} | {j['p99']:.4f} s | {j['max']:.4f} s | {d['design_mean']:.4f} s | {d['req_mean']:.4f} s |")
lines+=['','| 解法 | end_sec平均 | p95 | p99 | 最大 | >1.8 / >1.9 / >2.0 s |','|---|---:|---:|---:|---:|---:|']
for run in runs:
 d=summary[run]['end_sec'];lines.append(f"| {run.split('_',1)[1]} | {d['mean']:.4f} | {d['p95']:.4f} | {d['p99']:.4f} | {d['max']:.4f} | {d['over_1.8']}/{d['over_1.9']}/{d['over_2.0']} |")
lines+=['','通常run: '+', '.join('`'+r+'`' for r in runs)+'.',
'評価外のCPU負荷（平均/最大core）: '+', '.join(f"{r.split('_',1)[1]} {summary[r]['outside_load'].get('mean_cores')}/{summary[r]['outside_load'].get('max_cores')}" for r in runs)+'.',
'','## 固定した最終案の未使用seedでのリプレイ','',
'seed 500–999を設定選択に使わず、ソースと設定を`FROZEN.json`に固定してから測った。各seedで指定した注文列のコストを算術平均し、その比のlogをケース間で平均した。列1–7を主判定にする。','',
'| 注文列 | nofb比 ± SE | 操作/注文の差 | W/T/L |','|---|---:|---:|---:|']
for key,label in [('fresh','1–7（新しい注文列）'),('all','全8列'),('real','0（実列）')]:
 d=quality['results'][key];lines.append(f"| {label} | {d['mean']:+.4f} ± {d['se']:.4f}% | {d['moves_per_order']:+.6f} | {'/'.join(map(str,d['wtl']))} |")
lines+=['','リプレイrun: `'+eval['baseline_replay']+'` / `'+eval['candidate_replay']+'`. 保存設計は上記通常2000ケースrunのもの。',
'',f"`main.cpp`: **{len(source):,} bytes**（上限520,000 bytes）。SHA-256: `{hashlib.sha256(source).hexdigest()}`。",'']
(S/'FINAL_METRICS.md').write_text('\n'.join(lines))
print(json.dumps({'solution':S.name,'fresh':quality['results']['fresh'],'time':last['time_comparisons'][runs[0]],'p99':last['judge']['p99'],'base_p99':ref['judge']['p99'],'verdict':verdict},ensure_ascii=False,indent=2))
