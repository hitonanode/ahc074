from pathlib import Path
from collections import defaultdict
import argparse,json,re
p=argparse.ArgumentParser();p.add_argument('run');p.add_argument('--base');p.add_argument('--json');a=p.parse_args()
r=Path('/home/sato/ahc074/runs')/a.run
sums=defaultdict(float);n=0;equal=0
for d in [r]+sorted((r/'orders').glob('*')):
 for f in sorted((d/'err').glob('*.txt')):
  vals=dict(re.findall(r'^(r1_\w+|self_wrong|op_label_errors) = ([-+\d.eE]+)$',f.read_text(),re.M))
  if not vals:continue
  n+=1
  for k,v in vals.items():sums[k]+=float(v)
  if a.base:
   other=Path('/home/sato/ahc074/runs')/a.base/d.relative_to(r)/'out'/f.name
   equal+=(d/'out'/f.name).read_bytes()==other.read_bytes()
out={'cases':n,'stdout_equal':equal,'totals':dict(sums),'per_case':{k:v/n for k,v in sums.items()}}
print(json.dumps(out,ensure_ascii=False,indent=2))
if a.json:Path(a.json).write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
