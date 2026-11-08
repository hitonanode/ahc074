from pathlib import Path
import json,re,collections
N=Path(__file__).resolve().parent;R=Path('/home/sato/ahc074/runs');out={}
for cc in ['gcc','clang']:
 log=N/f't11-evisprof-{cc}.log'
 if not log.exists():continue
 rid=re.findall(r'^\[pahcer_run\] run-id: (\S+evis-prof)$',log.read_text(),re.M)
 if not rid:continue
 d=R/rid[0]
 if not(d/'result.json').exists():continue
 total=collections.defaultdict(float);n=0
 for seed in range(200):
  p=d/'err'/f'{seed:04d}.txt'
  if not p.exists():break
  n+=1
  for line in p.read_text().splitlines():
   z=line.split(' = ')
   if len(z)==2 and (z[0].startswith('cfprof_') or z[0]in['eject_pairs','eject_trials','eject_accepts']):
    total[z[0]]+=float(z[1])
 if n!=200:continue
 out[cc]={'run':rid[0],'n':n,'means':{k:v/n for k,v in total.items()}}
 print(cc,json.dumps(out[cc],ensure_ascii=False))
(N/'t11-evisprof-summary.json').write_text(json.dumps(out,indent=2)+'\n')
