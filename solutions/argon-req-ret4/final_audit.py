from pathlib import Path
import subprocess,re,json,hashlib,os
p=Path('solutions/argon-req-ret4');root=Path('/home/sato/ahc074/runs')
nb='20261105-231421_esw-slim';nc='20261105-231421_argon-req-ret4-late'
fb='20261105-230220_esw-slim';fc='20261105-230220_argon-req-ret4-late';fs='20261105-230220_argon-req-ret4-late-short'
with (p/'normal-2000.txt').open('w') as f:
 subprocess.run(['python3',str(p/'analyze.py'),nb,nc,'--json',str(p/'normal-2000.json')],stdout=f,check=True)
task_env=dict(os.environ,OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
with (p/'judge-model.txt').open('w') as f:
 subprocess.run(['/home/sato/ahc074/.venv/bin/python','/tmp/claude-1000/-home-sato-ahc074--claude-worktrees-esw-fixiter-improvement-55c629/4b08d16a-e458-4ef7-a878-a32403e05bc1/scratchpad/argon/judge_model.py',nb,nc],stdout=f,env=task_env,check=True)
text=Path('solutions/argon-req-ret4-late/main.cpp').read_bytes()
assert text==(root/fc/'src/main.cpp').read_bytes()==(root/nc/'src/main.cpp').read_bytes()
base=Path('solutions/esw-slim/main.cpp').read_text();cand=text.decode()
pat=re.compile(r'^\s*// ==== (.*?) ====\s*$',re.M)
def sections(s):
 m=list(pat.finditer(s));return {'header':s[:m[0].start()],**{x[1]:s[x.start():(m[i+1].start() if i+1<len(m) else len(s))] for i,x in enumerate(m)}}
ba,ca=sections(base),sections(cand);assert list(ba)==list(ca)
changed=[k for k in ba if ba[k]!=ca[k]]
allowed={'Request plans: options, fillers and the joint interval DP','Request plans: one plan (run_plan) and its shared tail','Request processing (process)','main: statistics'}
assert set(changed)<=allowed,changed
counts={'normal_cases':0,'design_equal':0,'attributes_equal':0,'metric_names_preserved':0,'normal_matches_fixed':0,'short_variant_files':0,'short_variant_identical':0}
for i in range(2000):
 name=f'{i:04d}.txt'
 bo=(root/nb/'out'/name).read_bytes();co=(root/nc/'out'/name).read_bytes()
 be=(root/nb/'err'/name).read_text();ce=(root/nc/'err'/name).read_text()
 counts['normal_cases']+=1
 counts['design_equal']+=bo.splitlines()[:192]==co.splitlines()[:192]
 counts['attributes_equal']+=[x for x in be.splitlines() if x.startswith('@paper ')]==[x for x in ce.splitlines() if x.startswith('@paper ')]
 names=lambda t:re.findall(r'^(\w+) = ',t,re.M)
 counts['metric_names_preserved']+=names(be)==[x for x in names(ce) if not x.startswith('r1_late_')]
 counts['normal_matches_fixed']+=co==(root/fc/'out'/name).read_bytes()
 for j in range(2):
  d=Path('.') if j==0 else Path('orders')/str(j)
  counts['short_variant_files']+=1
  counts['short_variant_identical']+=(root/fc/d/'out'/name).read_bytes()==(root/fs/d/'out'/name).read_bytes()
assert all(counts[k]==2000 for k in ['normal_cases','design_equal','attributes_equal','metric_names_preserved','normal_matches_fixed'])
assert counts['short_variant_identical']==4000
out={'sha256':hashlib.sha256(text).hexdigest(),'lines_before':len(base.splitlines()),'lines_after':len(cand.splitlines()),'changed_sections':changed,'counts':counts,'normal_run':nc,'fixed_run':fc}
p.joinpath('final-audit.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
