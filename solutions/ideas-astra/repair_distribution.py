from pathlib import Path
import json,re,statistics
root=Path('/home/sato/ahc074/runs/20261109-100609_ia-map-repair-audit/err')
rows=[]
for p in sorted(root.glob('*.txt')):
 text=p.read_text();d={k:float(v) for k,v in re.findall(r'^(ia_map_repair_\w+) = ([-+0-9.eE]+)$',text,re.M)}
 choices=[]
 for match in re.finditer(r'^@ia_map_repair (.+)$',text,re.M):
  x=list(map(float,match.group(1).split()));choices.append({'pool':int(x[0]),'gap':x[1],'swaps':int(x[2]),'targets':int(x[7])})
 rows.append({'seed':int(p.stem),'best_targets':d['ia_map_repair_released_targets_best'],'choices':choices})
a=sorted(r['best_targets'] for r in rows)
out={'n':len(a),'best_targets_mean':statistics.mean(a),'best_targets_p50':a[len(a)//2],'best_targets_p90':a[int(.90*(len(a)-1))],'best_targets_max':max(a),'best_targets_le48':sum(v<=48 for v in a),'best_targets_le64':sum(v<=64 for v in a),'best_targets_le80':sum(v<=80 for v in a),'any_targets_le48_gap_le002':sum(any(x['targets']<=48 and x['gap']<=.02 for x in r['choices']) for r in rows),'any_targets_le64_gap_le002':sum(any(x['targets']<=64 and x['gap']<=.02 for x in r['choices']) for r in rows),'max_seed':max(rows,key=lambda x:x['best_targets'])['seed']}
print(json.dumps(out,indent=2));Path('solutions/ideas-astra/repair-distribution.json').write_text(json.dumps(out,indent=2)+'\n')
