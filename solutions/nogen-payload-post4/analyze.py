"""保存結果の集計・所有色と表示の監査。共有runs/.lockの下で実行する。"""
from pathlib import Path
import hashlib,json,math,statistics,sys
ROOT=Path('/home/sato/ahc074/runs')
def scores(n):
 return {c['seed']:c['score'] for c in json.loads((ROOT/n/'result.json').read_text())['cases']}
def compare(a,b):
 keys=sorted(a.keys()&b.keys());assert all(a[k]>0 and b[k]>0 for k in keys)
 d=[100*math.log(a[k]/b[k]) for k in keys]
 return dict(n=len(d),log_pct=statistics.mean(d),SE=statistics.stdev(d)/math.sqrt(len(d)),WTL=[sum(a[k]<b[k] for k in keys),sum(a[k]==b[k] for k in keys),sum(a[k]>b[k] for k in keys)])
def q(v,p):
 v=sorted(v);x=(len(v)-1)*p;i=int(x);return v[i]+(v[min(i+1,len(v)-1)]-v[i])*(x-i)
ref=scores('20261106-085703_argon-des-perf-latew105');old=scores('20261106-113548_nogen-perf-reuse')
all_scores={n:scores(n) for n in sys.argv[1:]}
for n in sys.argv[1:]:
 sc=all_scores[n];assert set(sc)==set(range(2000)),(n,len(sc))
 c=json.loads((ROOT/n/'metrics.json').read_text())['cases'];m={int(k):v['stderr'] for k,v in c.items()};js={k:x['end_sec']+.04*x['helper_end_sec']+.35*x['req_sec'] for k,x in m.items()};v=list(js.values())
 print(n,json.dumps(dict(mean_score=statistics.mean(sc.values()),WA=sum(x<=0 for x in sc.values()),E=sum(x['E'] for x in c.values()),sota=compare(sc,ref),previous_best=compare(sc,old),judge=dict(mean=statistics.mean(v),p99=q(v,.99),maximum=max(v),over2=sum(x>2 for x in v),worst=sorted(js.items(),key=lambda kv:-kv[1])[:5])),ensure_ascii=False))
 if 'nogen-payload-' in n:
  assert all(x['E']==0 and x['requests']==1024 for x in c.values())
  for x in m.values():
   assert all(x[k]==0 for k in ['audit_owner_violations','audit_cap_violations','audit_unowned_papers','self_wrong','op_label_errors'])
   assert x['audit_product_papers']==191 and x['audit_certificate_targets']==256
  keys=['audit_owner_violations','audit_cap_violations','audit_unowned_papers','audit_product_papers','audit_certificate_targets','inverse_map_iters','inverse_climb_iters','control_anneal_iters','control_climb_iters','light_requests','helper_end_sec','req_sec','end_sec']
  print('metrics',json.dumps({k:dict(mean=statistics.mean(x[k] for x in m.values() if k in x),minimum=min(x[k] for x in m.values() if k in x),maximum=max(x[k] for x in m.values() if k in x)) for k in keys if any(k in x for x in m.values())}))
  p=ROOT/n;meta=json.loads((p/'meta.json').read_text());print('outside',meta.get('outside_load'),[x.get('outside_load') for x in meta.get('extensions',[])])
  source=Path('solutions')/n.split('_',1)[1]/'main.cpp';print('source_matches',hashlib.sha256((p/'src/main.cpp').read_bytes()).digest()==hashlib.sha256(source.read_bytes()).digest(),'saved_designs',len(list((p/'design').glob('*'))))
for i,a in enumerate(sys.argv[1:]):
 for b in sys.argv[2+i:]:print('pair',a,b,compare(all_scores[a],all_scores[b]))
