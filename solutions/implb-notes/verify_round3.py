from pathlib import Path
import json
root=Path('/home/sato/ahc074/runs')
checks=[]
for name,n in [('20261109-132432_d30a-reset6',2000),('20261109-132432_d30b-cover040',500),('20261109-132432_d30b-cover045',500),('20261109-132432_d30b-cover050',2000),('20261109-134929_d30a-reset6',500),('20261109-134929_d30b-ramp-a',500),('20261109-134929_d30b-ramp-b',500)]:
 p=root/name;m=json.loads((p/'meta.json').read_text());c=json.loads((p/'result.json').read_text())['cases']
 assert len(c)==n and all(min(x.get('order_scores') or [x['score']])>0 for x in c)
 solver=Path('solutions')/name.split('_',1)[1]/'main.cpp'
 assert solver.read_bytes()==(p/'src/main.cpp').read_bytes()
 checks.append({'run':name,'n':n,'wa':0,'source_unchanged':True,'status':m['status']})
prefix=[]
for name in ['20261109-133747_d30a-reset6','20261109-133747_d30b-cover050','20261109-133747_d30b-cover050-2']:
 p=root/name;m=json.loads((p/'meta.json').read_text());c=json.loads((p/'result.json').read_text())['cases'];assert len(c)==20 and all(x['score']>0 for x in c)
 if 'd30b-' in name:assert '-DNEXT_PREFIX_CHECK' in m['compile_command']
 prefix.append({'run':name,'wa':0,'jflags':m['jflags']})
identity=[]
base=root/'20261109-132202_d30a-reset6'
for s in ['040','045','050']:
 p=root/('20261109-132202_d30b-cover'+s)
 same=sum((base/'out'/f'{i:04d}.txt').read_bytes().splitlines()[:192]==(p/'out'/f'{i:04d}.txt').read_bytes().splitlines()[:192] for i in range(20))
 assert same==20;identity.append({'candidate':p.name,'designs_equal':same})
r={'runs':checks,'prefix_check':prefix,'normal_smoke_designs':identity}
Path('solutions/implb-notes/round3-verification.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
