"""Cross-check final times with the task's unchanged judge_model.py (run under flock)."""
from pathlib import Path
import sys,json,subprocess,re,os
P=Path(__file__).resolve().parent;root=P.parents[1];D=root/'solutions'/sys.argv[1]
scratch=P/'reference'
import hashlib
for name,row in json.loads((scratch/'sources.json').read_text()).items():assert hashlib.sha256((scratch/name).read_bytes()).hexdigest()==row['sha256']
x=json.loads((D/'final-metrics.json').read_text());ids=x['run_ids']['normal'];names=['argon-des-perf-latew105','deval-vbranch-nofb','deval-flex125-plan3',D.name];runs=[next(r for r in ids if r.endswith('_'+n)) for n in names]
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1')
r=subprocess.run([sys.executable,str(scratch/'judge_model.py'),*runs],cwd=root,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,check=True)
(D/'judge-model.txt').write_text(r.stdout)
for line in r.stdout.splitlines():
 rid=line.split(':',1)[0];assert rid in runs
 vals=re.search(r'judge mean (\S+)  p99 (\S+)  max (\S+)',line);assert vals
 for k,v in zip(['mean','p99','max'],vals.groups()):assert abs(float(v)-x['normal'][rid]['judge'][k])<=.000501,(rid,k,v)
assert len(r.stdout.splitlines())==4
if not json.loads((D/'FROZEN.json').read_text())['request_only']:
 z=subprocess.run([sys.executable,str(scratch/'cmp_variant.py'),x['run_ids']['reference'],x['run_ids']['replay']],cwd=root,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,check=True)
 (D/'cmp-variant.txt').write_text(z.stdout)
(D/'official-check.json').write_text(json.dumps({'judge_model_matches':True,'script':str(scratch/'judge_model.py'),'runs':runs},indent=2)+'\n')
print(r.stdout)
