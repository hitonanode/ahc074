from pathlib import Path
import json,subprocess,sys
root=Path(__file__).resolve().parents[2];runs=Path('/home/sato/ahc074/runs')
variants=json.loads((root/'solutions/implb-notes/cost-screen.json').read_text())
for x in variants:
 ds=sorted(runs.glob('*_'+Path(x['path']).name))
 assert ds,(x,'no smoke')
 r=json.loads((ds[-1]/'result.json').read_text())
 cases=r['cases'];assert len(cases)==20 and all(c['score']>0 for c in cases),(ds[-1],'smoke failed')
 print('SMOKE OK',ds[-1].name,flush=True)
args=[sys.executable,'solutions/implb-notes/cached_run.py','--compare','solutions/d30a-stack1']+[x['path'] for x in variants]+['--seeds','0-500','-c','B stack1 design-model constants screen: 8 knobs x2, fixed iterations, V unchanged']
with (root/'solutions/implb-notes/cost-500.log').open('w') as f:
 subprocess.run(args,cwd=root,stdout=f,stderr=subprocess.STDOUT,check=True)
print('SCREEN COMPLETE',flush=True)
ids=[]
for x in variants:
 ds=sorted(runs.glob('*_'+Path(x['path']).name));ids.append(ds[-1].name)
group=json.loads((runs/ids[0]/'meta.json').read_text())['compare']['runs'];base=group[0]
assert group[1:]==ids
assert (runs/base/'result.json').exists()
(root/'solutions/implb-notes/cost-500-runs.json').write_text(json.dumps([base]+ids,indent=2)+'\n')
with (root/'solutions/implb-notes/cost-500-summary.txt').open('w') as f:
 subprocess.run(['flock','-x','/home/sato/ahc074/runs/.lock','nice','-n','10',sys.executable,'solutions/implb-notes/summarize.py',base]+ids+['--output','solutions/implb-notes/cost-500.json'],cwd=root,stdout=f,stderr=subprocess.STDOUT,check=True)
print('ANALYSIS COMPLETE',flush=True)
