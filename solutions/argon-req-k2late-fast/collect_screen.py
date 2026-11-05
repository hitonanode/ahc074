from pathlib import Path
import subprocess,json,re,statistics
p=Path('solutions/argon-req-k2late-fast')
r='20261106-060735_'
names=['argon-req-ejectstats-v2','argon-req-k2late-cheap','argon-req-k2late-fast','argon-req-newfull-liftfirst','argon-req-seedfinish-probe']
for prefix,namelist,out in [(r,names,'screen'),('20261106-060200_',names[:2]+['argon-req-k2late-edit'],'late')]:
 with (p/(out+'-analysis.log')).open('w') as f:
  subprocess.run(['python3','solutions/argon-req-completeold/analyze.py',*[prefix+n for n in namelist],'--end','200','--json',str(p/(out+'-results.json'))],stdout=f,check=True)
with (p/'exact.log').open('w') as f:
 subprocess.run(['python3','solutions/argon-req-exactprofile/check_exact.py',r+names[1],r+names[2]],stdout=f,check=True)
root=Path('/home/sato/ahc074/runs')
results={}
for name in names:
 d=root/(r+name); rows=[]
 for file in sorted(d.glob('out/*.txt'))+sorted(d.glob('orders/*/out/*.txt')):
  rel=file.relative_to(d); err=rel.parent.parent/'err'/rel.name
  text=(d/err).read_text()
  m={k:float(v) for k,v in re.findall(r'^(\w+) = ([-+\d.eE]+)$',text,re.M)}
  assert m['self_wrong']==m['op_label_errors']==0
  if name.endswith('probe'):
   assert file.read_bytes()==(root/(r+names[0])/rel).read_bytes()
   assert [l for l in text.splitlines() if l.startswith('@')]==[l for l in (root/(r+names[0])/err).read_text().splitlines() if l.startswith('@')]
  rows.append(m)
 results[name]={k:statistics.mean(x[k] for x in rows) for k in rows[0] if k.startswith(('joint_late_','joint_extra_','seed_probe_','seed_finish_','old_full_','value_seed_')) or k in ['req_sec','total_moves']}
(p/'metrics.json').write_text(json.dumps(results,indent=2)+'\n')
print('Screen/exact/oracle checks passed',flush=True)
