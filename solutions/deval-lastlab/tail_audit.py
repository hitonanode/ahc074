"""Record the largest measured judge times without excluding any case."""
from pathlib import Path
import json,sys
P=Path(__file__).resolve().parent;R=Path('/home/sato/ahc074/runs');D=P.parent/sys.argv[1]
x=json.loads((D/'final-metrics.json').read_text());ids=x['run_ids']['normal'];names=[D.name,'deval-flex125-plan3','deval-vbranch-nofb']
runs={n:next(r for r in ids if r.endswith('_'+n)) for n in names}
ms={n:{int(i):v['stderr'] for i,v in json.loads((R/r/'metrics.json').read_text())['cases'].items()} for n,r in runs.items()}
def judge(z):return 1.04*z['helper_end_sec']+1.35*z['req_sec']+z['end_sec']-z['helper_end_sec']-z['req_sec']
keys=['map_end_sec','dv_anneal_sec','dv_finish_sec','helper_end_sec','req_sec','end_sec']
top=sorted(range(2000),key=lambda i:judge(ms[D.name][i]),reverse=True)[:5]
rows=[]
for i in top:
 rows.append({'seed':i,'solutions':{n:{**{k:ms[n][i][k] for k in keys},'judge':judge(ms[n][i])} for n in names}})
(D/'tail-audit.json').write_text(json.dumps({'runs':runs,'cases':rows},indent=2)+'\n')
lines=['最大側5ケースの実測値（除外や補正はしていない）:','','| seed | 候補judge s | flex125 judge s | nofb judge s | 候補design / flex design s | 候補req / flex req s |','|---|---:|---:|---:|---:|---:|']
for z in rows:
 c=z['solutions'][D.name];b=z['solutions']['deval-flex125-plan3'];f=z['solutions']['deval-vbranch-nofb']
 lines.append(f"| {z['seed']} | {c['judge']:.6f} | {b['judge']:.6f} | {f['judge']:.6f} | {c['helper_end_sec']:.6f} / {b['helper_end_sec']:.6f} | {c['req_sec']:.6f} / {b['req_sec']:.6f} |")
(D/'TAIL.md').write_text('\n'.join(lines)+'\n')
print('\n'.join(lines))
