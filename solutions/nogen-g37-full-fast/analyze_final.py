"""保存結果だけを読む集計。共有 runs/.lock を保持して実行する。"""
import hashlib,json,math,statistics
from pathlib import Path
ROOT=Path('/home/sato/ahc074/runs')
RUNS=['20261106-133437_argon-des-perf-latew105','20261106-133437_nogen-g37-deep-fast','20261106-133437_nogen-g37-full-fast','20261106-113548_nogen-perf-reuse','20261106-130407_nogen-true-demand']
def scores(name):
 return {c['seed']:c['score'] for c in json.loads((ROOT/name/'result.json').read_text())['cases']}
def compare(a,b):
 keys=sorted(a.keys()&b.keys());keys=[k for k in keys if a[k]>0 and b[k]>0]
 d=[100*math.log(a[k]/b[k]) for k in keys]
 return dict(n=len(d),log_pct=statistics.mean(d),SE=statistics.stdev(d)/math.sqrt(len(d)),WTL=[sum(a[k]<b[k] for k in keys),sum(a[k]==b[k] for k in keys),sum(a[k]>b[k] for k in keys)])
def quantile(v,p):
 v=sorted(v);x=(len(v)-1)*p;i=int(x);return v[i]+(v[min(i+1,len(v)-1)]-v[i])*(x-i)
for name in RUNS[:3]: assert set(scores(name))==set(range(2000)), name
ref=scores('20261106-085703_argon-des-perf-latew105');old=scores(RUNS[3]);all_scores={r:scores(r) for r in RUNS}
for name in RUNS:
 c=json.loads((ROOT/name/'metrics.json').read_text())['cases'];m={int(k):v['stderr'] for k,v in c.items()};sc=all_scores[name]
 judge={k:v['end_sec']+.04*v['helper_end_sec']+.35*v['req_sec'] for k,v in m.items()};v=list(judge.values())
 print(name,json.dumps(dict(mean_score=statistics.mean(sc.values()),WA=sum(x<=0 for x in sc.values()),E=sum(x['E'] for x in c.values()),sota=compare(sc,ref),previous_best=compare(sc,old),judge=dict(mean=statistics.mean(v),p99=quantile(v,.99),maximum=max(v),over2=sum(x>2 for x in v),worst=sorted(judge.items(),key=lambda kv:-kv[1])[:5])),ensure_ascii=False))
 keys=['audit_owner_violations','audit_cap_violations','audit_unowned_papers','audit_product_papers','audit_certificate_targets','self_wrong','op_label_errors','inverse_map_iters','inverse_climb_iters','control_anneal_iters','control_climb_iters','light_requests','helper_end_sec','req_sec','end_sec']
 print('metrics',json.dumps({k:dict(mean=statistics.mean(x[k] for x in m.values() if k in x),min=min(x[k] for x in m.values() if k in x),max=max(x[k] for x in m.values() if k in x)) for k in keys if any(k in x for x in m.values())}))
 if name==RUNS[2]:
  assert all(x['E']==0 and x['requests']==1024 for x in c.values())
  for x in m.values():
   assert all(x[k]==0 for k in ['audit_owner_violations','audit_cap_violations','audit_unowned_papers','self_wrong','op_label_errors'])
   assert x['audit_product_papers']==191 and x['audit_certificate_targets']==256
  print('vs_deep',compare(sc,all_scores[RUNS[1]]),'vs_true_demand',compare(sc,all_scores[RUNS[4]]))
  path=ROOT/name
  print('saved_designs',len(list((path/'design').glob('*'))))
  meta=json.loads((path/'meta.json').read_text());print('outside',meta.get('outside_load'),[(x.get('outside_load')) for x in meta.get('extensions',[])])
  print('source_matches',hashlib.sha256((path/'src/main.cpp').read_bytes()).hexdigest()==hashlib.sha256(Path(__file__).with_name('main.cpp').read_bytes()).hexdigest())
