"""Compare saved stdout and non-timing stderr. Never executes a solution or tester."""
from pathlib import Path
import argparse,json,re
p=argparse.ArgumentParser();p.add_argument('baseline');p.add_argument('candidate');p.add_argument('--end',type=int,default=2000);p.add_argument('--json');p.add_argument('--profiles',action='store_true');a=p.parse_args()
root=Path('/home/sato/ahc074/runs')
b=root/a.baseline;c=root/a.candidate
metric=re.compile(r'^([\w]+) = ([-+\d.eE]+)$')
def non_time(path):
 out=[]
 for line in path.read_text().splitlines():
  m=metric.match(line)
  if m and m[1].endswith('_sec'):continue
  if a.profiles:
   if m and m[1].startswith('cfprof_') and m[1].endswith(('_inc','_exc')):continue
   if line.startswith(('#f3post ', '#f3op ')):line=line.rsplit(' ',1)[0]
  out.append(line)
 return out
counts={'files':0,'stdout_equal':0,'stderr_equal':0,'mismatches':[]}
for d in [c]+sorted((c/'orders').glob('*')):
 if not (d/'out').is_dir():continue
 rel=d.relative_to(c);bd=b/rel
 for f in sorted((d/'out').glob('*.txt')):
  if int(f.stem)>=a.end:continue
  bf=bd/'out'/f.name
  if not bf.exists():continue
  counts['files']+=1
  eq=f.read_bytes()==bf.read_bytes();counts['stdout_equal']+=eq
  x=non_time(bd/'err'/f.name);y=non_time(d/'err'/f.name);se=x==y;counts['stderr_equal']+=se
  if not(eq and se):
   first=next(((i,u,v) for i,(u,v) in enumerate(zip(x,y)) if u!=v),None)
   counts['mismatches'].append({'file':str(rel/'out'/f.name),'stdout':eq,'stderr':se,'first':first,'lines':[len(x),len(y)]})
print(json.dumps(counts,ensure_ascii=False,indent=2))
if a.json:Path(a.json).write_text(json.dumps(counts,ensure_ascii=False,indent=2)+'\n')
