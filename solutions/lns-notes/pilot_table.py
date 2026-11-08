from pathlib import Path
import json,math,statistics
here=Path(__file__).resolve().parent;R=Path('/home/sato/ahc074/runs')
base={c['seed']:c for c in json.loads((R/'20261108-040819_deval-helper-wide/result.json').read_text())['cases']}
out=[]
for tag in ['pilot2','pilot-warm','pilot-cool','pilot-joint','pilot-control','pilot-reheat','pilot8','pilot-graph','pilot-cut','pilot-reheat8','pilot-warmhole','pilot-preferred','pilot-soft','pilot-distinct','pilot-long8','pilot-deepmap8','pilot-untrap','pilot-star8']:
 p=here/(tag+'.json')
 if not p.exists():continue
 for row in json.loads(p.read_text()):
  run=row['replay'];m=json.loads((R/run/'meta.json').read_text());assert m['status']=='ok';cs=json.loads((R/run/'result.json').read_text())['cases'];d=[];r=[]
  for c in cs:
   x=statistics.mean(base[c['seed']]['order_scores'][1:]);y=statistics.mean(c['order_scores'][1:]);d.append((y-x)/1024);r.append(100*math.log(y/x))
  z={'tag':tag,'source':Path(row['source']).name,'replay':run,'n':len(d),'moves':statistics.mean(d),'moves_se':statistics.stdev(d)/len(d)**.5,'pct':statistics.mean(r),'pct_se':statistics.stdev(r)/len(r)**.5,'outside_load':m.get('outside_load')};out.append(z)
  print(f"{z['source']:48s} {z['moves']:+.5f} ±{z['moves_se']:.5f}  {z['pct']:+.4f} ±{z['pct_se']:.4f}%")
(here/'pilot-table.json').write_text(json.dumps(out,indent=2)+'\n')
