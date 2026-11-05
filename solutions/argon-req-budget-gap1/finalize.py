from pathlib import Path
import re, statistics as st, json, subprocess, sys
here=Path(__file__).parent;root=Path('/home/sato/ahc074/runs')
base=root/'20261106-080510_argon-des-perf-latew105'
trial=root/'20261106-080510_argon-req-budget-gap1'
def norm(text):
 return [line for line in text.splitlines() if not re.match(r'^\w+_sec = ',line)
         and not line.startswith(('budget_requests =','budget_triples =','budget_plan_skipped ='))]
files=0
for f in sorted(trial.glob('out/*.txt'))+sorted(trial.glob('orders/*/out/*.txt')):
 rel=f.relative_to(trial);err=rel.parent.parent/'err'/rel.name
 assert f.read_bytes()==(base/rel).read_bytes(),str(rel)
 assert norm((trial/err).read_text())==norm((base/err).read_text()),str(err)
 files+=1
assert files==16
print('ARGON_ADAPT=0: stdout and ALL original non-time stderr identical',files,flush=True)
(here/'off-equality.json').write_text(json.dumps({'stdout':files,'non_time_stderr':files},indent=2)+'\n')
rx=re.compile(r'^(\w+) = ([-+\d.eE]+)$',re.M);metrics={}
for suffix in ['argon-des-perf-latew105','argon-req-budget-adapt','argon-req-budget-gap1']:
 run=root/('20261106-080224_'+suffix);rows=[]
 for f in list(run.glob('err/*.txt'))+list(run.glob('orders/*/err/*.txt')):
  rows.append({k:float(v) for k,v in rx.findall(f.read_text())})
 fields=[k for k in rows[0] if k.startswith(('budget_','ns_','f2_plan','neutral_'))]
 metrics[suffix]={k:st.mean(r[k] for r in rows) for k in fields}
(here/'metrics.json').write_text(json.dumps(metrics,indent=2)+'\n')
print('budget/neutral metrics',metrics,flush=True)
for stamp,suffix in [('20261106-074004','argon-req-budgetprobe'),('20261106-075108','argon-req-budgetparts')]:
 subprocess.run([sys.executable,'solutions/argon-req-completeold/analyze.py',stamp+'_argon-des-perf-latew105',stamp+'_'+suffix,'--end','200','--json',str(Path('solutions')/suffix/'results.json')],check=True)
source=Path('solutions/argon-des-perf-latew105/main.cpp').read_text();s=(here/'main.cpp').read_text()
assert re.findall(r'^\s*// ==== .*',source,re.M)==re.findall(r'^\s*// ==== .*',s,re.M)
assert source[:source.index('#include')]==s[:s.index('#include')]
assert 'All four builds passed with no warnings.' in (here/'builds.log').read_text()
print('4 builds passed; header and section markers preserved',flush=True)
