from pathlib import Path
import sys, re, subprocess, statistics, json
p=Path(__file__).resolve().parent
log=Path(sys.argv[1])
names=list(dict.fromkeys(re.findall(r'run-id: (\S+)',log.read_text())))
if not names:
 names=list(dict.fromkeys(re.findall(r'(202\d{5}-\d{6}_argon-req-[\w-]+)',log.read_text())))
assert names, log
subprocess.run([sys.executable,str(p/'analyze.py'),*names,'--json',str(log.with_suffix('.json'))],check=True)
res={}
for name in names:
 r=Path('/home/sato/ahc074/runs')/name
 files=list((r/'err').glob('*.txt'))+list((r/'orders').glob('*/err/*.txt'))
 rows=[dict((k,float(v)) for k,v in re.findall(r'^(\w+) = ([-+\d.eE]+)$',f.read_text(),re.M)) for f in files]
 keys=[k for k in rows[0] if k.startswith(('old_complete_','joint_extra_','complete_value_','value_seed_','eject_yield_'))]
 res[name]={k:statistics.mean(row.get(k,0) for row in rows) for k in keys}
 assert all(row.get('self_wrong')==0 and row.get('op_label_errors')==0 for row in rows),name
 print(name, json.dumps(res[name],ensure_ascii=False),flush=True)
log.with_name(log.stem+'-metrics.json').write_text(json.dumps(res,indent=2)+'\n')
