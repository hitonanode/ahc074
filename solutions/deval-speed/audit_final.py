"""Audit saved artifacts only; never execute a solution. Use under the shared flock."""
from pathlib import Path
import argparse,json,hashlib,re
p=argparse.ArgumentParser();p.add_argument('solution');p.add_argument('normal');p.add_argument('replay');p.add_argument('--output');a=p.parse_args()
R=Path('/home/sato/ahc074/runs');S=Path(a.solution);source=(S/'main.cpp').read_bytes();text=source.decode()
markers=re.findall(r'^[ \t]*// ==== (.*?) ====$',text,re.M)
header=text[:text.index('#include')]
toc=re.findall(r'^//   (.+)$',header,re.M)
checks={'source_bytes':len(source),'source_sha256':hashlib.sha256(source).hexdigest(),'source_size_ok':len(source)<=520000,'marker_count':len(markers),'toc_matches':markers==toc,
 'no_bits_stdcpp':'bits/stdc++.h' not in text,'no_fast_math':'fast-math' not in text and 'Ofast' not in text,
 'no_request_guard':'DEVAL_REQUEST_LIMIT' not in text and 'light_requests' not in text,'no_candidate_guard':'DEVAL_DESIGN_LIMIT' not in text}
for run in [a.normal,a.replay]:
 checks[run+'_source_matches']=(R/run/'src/main.cpp').read_bytes()==source
 results=json.loads((R/run/'result.json').read_text())['cases']
 checks[run+'_wa']=sum(any(s<=0 for s in row.get('order_scores',[row['score']])) for row in results)
 meta=json.loads((R/run/'meta.json').read_text())
 checks[run+'_outside_load']=meta.get('outside_load')
normal={int(r['seed']):r for r in json.loads((R/a.normal/'result.json').read_text())['cases']}
replay={int(r['seed']):r for r in json.loads((R/a.replay/'result.json').read_text())['cases']}
checks['replay_normal_real_list_matches']=sum(normal[k]['score']==r['order_scores'][0] for k,r in replay.items() if k in normal)
checks['replay_common_cases']=len(set(normal)&set(replay))
checks['replay_stdout_identical']=sum((R/a.normal/'out'/f.name).read_bytes()==f.read_bytes() for f in (R/a.replay/'out').glob('*.txt') if int(f.stem) in normal)
m=json.loads((R/a.normal/'metrics.json').read_text())['cases']
checks['op_label_errors']=sum(v['stderr'].get('op_label_errors',0) for v in m.values())
checks['replay_seeds']=[min(replay),max(replay)]
checks['replay_order_lists']=sorted(set(len(r['order_scores']) for r in replay.values()))
checks['normal_cases']=len(normal)
logs=list((R/a.replay/'err').glob('*.txt'))+list((R/a.replay/'orders').glob('*/err/*.txt'))
totals={'self_wrong':0,'op_label_errors':0}
for log in logs:
 with log.open('rb') as f:
  f.seek(0,2);length=f.tell();f.seek(max(0,length-16384));tail=f.read().decode(errors='replace')
 for key in totals:
  found=re.findall(r'^'+key+r' = (\d+)$',tail,re.M)
  assert found,(log,key)
  totals[key]+=int(found[-1])
checks['replay_order_executions']=len(logs)
checks['replay_all_orders_self_wrong']=totals['self_wrong']
checks['replay_all_orders_label_errors']=totals['op_label_errors']
checks['checks_pass']=all(v for k,v in checks.items() if k in ['source_size_ok','toc_matches','no_bits_stdcpp','no_fast_math','no_request_guard','no_candidate_guard'] or k.endswith('_source_matches')) and all(v==0 for k,v in checks.items() if k.endswith('_wa')) and checks['replay_normal_real_list_matches']==checks['replay_common_cases'] and checks['replay_stdout_identical']==checks['replay_common_cases'] and checks['op_label_errors']==0 and len(logs)==8*len(replay) and all(v==0 for v in totals.values())
out=Path(a.output) if a.output else S/'audit.json';out.write_text(json.dumps(checks,ensure_ascii=False,indent=2)+'\n');print(json.dumps(checks,ensure_ascii=False,indent=2))
