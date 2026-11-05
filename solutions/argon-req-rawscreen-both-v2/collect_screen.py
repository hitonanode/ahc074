from pathlib import Path
import subprocess,json,re,statistics as st
p=Path('solutions/argon-req-rawscreen-both-v2');prefix='20261106-062839_'
names=['argon-des-perf-rematch-v2','argon-req-k2direct-v2','argon-req-k2directwide-v2','argon-req-rawscreen-v2','argon-req-rawscreen-both-v2']
with (p/'screen-analysis.log').open('w') as f:
 subprocess.run(['python3','solutions/argon-req-completeold/analyze.py',*[prefix+n for n in names],'--end','200','--json',str(p/'screen-results.json')],stdout=f,check=True)
results={}
root=Path('/home/sato/ahc074/runs')
for name in names:
 d=root/(prefix+name);rows=[]
 for f in sorted(d.glob('err/*.txt'))+sorted(d.glob('orders/*/err/*.txt')):
  m={k:float(v) for k,v in re.findall(r'^(\w+) = ([-+\d.eE]+)$',f.read_text(),re.M)}
  assert m['self_wrong']==m['op_label_errors']==0
  rows.append(m)
 results[name]={k:st.mean(row[k] for row in rows) for k in rows[0] if k.startswith(('raw_joint_','joint_extra_','joint_late_','value_seed_')) or k in ['total_moves','req_sec']}
(p/'metrics.json').write_text(json.dumps(results,indent=2)+'\n')
with (p/'compact-exact.log').open('w') as f:
 subprocess.run(['python3','solutions/argon-req-exactprofile/check_exact.py','20261106-062412_argon-req-k2late-fast','20261106-062412_argon-req-k2late-compact'],stdout=f,check=True)
print('All screen diagnostics and compact exactness passed',flush=True)
