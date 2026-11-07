from pathlib import Path
import re,json,hashlib
P=Path(__file__).resolve().parent;R=Path('/home/sato/ahc074/runs');rows=[]
def check(log):
 ids=re.findall(r'^\[pahcer_run\] run-id: (\S+)',log.read_text(),re.M)
 assert len(ids)==2,(log,ids)
 a,b=ids
 ma=json.loads((R/a/'meta.json').read_text());mb=json.loads((R/b/'meta.json').read_text());assert ma['status']==mb['status']=='ok'
 ca=json.loads((R/a/'result.json').read_text())['cases'];cb=json.loads((R/b/'result.json').read_text())['cases'];assert len(ca)==len(cb)>=200
 seeds=sorted(int(x['seed']) for x in ca);assert seeds[-1]<500
 same=sum((R/a/'out'/f'{s:04d}.txt').read_bytes()==(R/b/'out'/f'{s:04d}.txt').read_bytes() for s in seeds)
 z={'log':log.name,'reference':a,'candidate':b,'n':len(seeds),'stdout_identical':same,'compiler':mb['compiler'],'flags':mb['compile_command'],'source_sha256':hashlib.sha256((R/b/'src/main.cpp').read_bytes()).hexdigest()}
 rows.append(z);assert same==len(seeds),z
for name in ['native-gcc.log','native-clang.log']:
 check(P/name)
for log in sorted(P.glob('last-identity-*.log')):check(log)
for log in sorted(P.glob('combined-*.log')):
 if log.name!='combined-checks.driver.log':check(log)
for name in ['hash2-gcc.log','hash2-clang.log']:
 log=P/name
 if log.exists():
  ids=re.findall(r'^\[pahcer_run\] run-id: (\S+)',log.read_text(),re.M)
  if ids and all(json.loads((R/i/'meta.json').read_text()).get('status')=='ok' for i in ids):check(log)
(P/'identity-extra.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
for z in rows:print(z['log'],z['n'],z['stdout_identical'])
