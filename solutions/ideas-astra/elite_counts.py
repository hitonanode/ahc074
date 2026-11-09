from pathlib import Path
import json,re,statistics
root=Path('/home/sato/ahc074/runs');out={}
for name in ['20261107-150327_deval-elite-branch','20261107-150327_deval-elite-close']:
 rows=[]
 for p in sorted((root/name/'err').glob('*.txt')):
  text=p.read_text();d={k:int(v) for k,v in re.findall(r'^(elite_total|elite_same_set|elite_alternates) = (\d+)$',text,re.M)}
  if len(d)==3:rows.append({'seed':int(p.stem),**d,'other_set':d['elite_total']-d['elite_same_set']})
 out[name]={'n':len(rows),'means':{k:statistics.mean(x[k] for x in rows) for k in ['elite_total','elite_same_set','elite_alternates','other_set']},'other_set_nonzero':sum(x['other_set']>0 for x in rows),'other_set_hist':{str(i):sum(x['other_set']==i for x in rows) for i in range(9)},'rows':rows}
 print(name,{k:v for k,v in out[name].items() if k!='rows'})
Path('solutions/ideas-astra/elite-counts.json').write_text(json.dumps(out,indent=2)+'\n')
