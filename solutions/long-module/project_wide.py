from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import subprocess,json
folder=Path(__file__).resolve().parent;out=folder/'wide-project';out.mkdir(exist_ok=True);jobs=[]
for seed in range(24,28):
 source=folder/'wide'/f'{seed:04d}-w5.json'
 if not source.exists():continue
 r=json.loads(source.read_text());profile=folder/'wide'/f'{seed:04d}-w5.txt';lines=profile.read_text().splitlines();allowed=[int(l.split()[4])for l in lines[1:1+r['papers']]]
 projected=[a&((1<<m.bit_length())-1)for m,a in zip(r['opaque'],allowed)]
 print('nonprefix',seed,[(k,a,b)for k,(a,b)in enumerate(zip(r['opaque'],projected))if a!=b],flush=True)
 for beam in (32,64):
  for label,masks in [('free',r['opaque']),('project',projected)]:jobs.append((seed,beam,label,masks))
def job(item):
 seed,beam,label,masks=item;profile=folder/'wide'/f'{seed:04d}-w5.txt';name=f'{seed:04d}-b{beam}-{label}';saved=out/f'{name}.json'
 if saved.exists():return json.loads(saved.read_text())
 with (out/f'{name}.err').open('w') as log:
  p=subprocess.run(['/tmp/ahc074-long-fast',str(profile),'0','256','65536',str(beam),','.join(map(str,masks)),'800000007','0','0'],stdout=subprocess.PIPE,stderr=log,text=True,timeout=600)
 if p.returncode==5:r={'infeasible':True}
 else:p.check_returncode();r=json.loads(p.stdout)
 r.update(seed=seed,beam=beam,label=label);saved.write_text(json.dumps(r,indent=2)+'\n');print(seed,beam,label,r.get('difference'),r.get('fallback'),flush=True);return r
with ThreadPoolExecutor(max_workers=2)as pool:rows=list(pool.map(job,jobs))
(out/'summary.json').write_text(json.dumps(rows,indent=2)+'\n')
