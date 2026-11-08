"""Replay the first four star local winners; reuse byte-identical base artifacts."""
from pathlib import Path
import json, subprocess, sys, time

h=Path(__file__).resolve().parent;r=Path('/home/sato/ahc074/runs')
source=sys.argv[1]
while True:
    m=json.loads((r/source/'meta.json').read_text())
    if m['status']=='ok':break
    assert m['status'] not in ['error','failed','compile_error']
    time.sleep(10)

subprocess.run(['flock','-x',str(r/'.lock'),'nice','-n','10',sys.executable,
                str(h/'group_star_artifacts.py'),str(h/'star-dump'),
                '--output',str(h/'star-grouped')],check=True)
subprocess.run([sys.executable,str(h/'prepare_artifacts.py'),str(h/'star-grouped'),
                '--source',source],check=True)
previous=json.loads((h/'diagnostic-joint.json').read_text())
shared=[]
for row in previous:
    original=Path(row['source']);cid=json.loads((original/'meta.json').read_text())['candidate_id']
    if cid not in [0,1,2,3,1000]:continue
    current=h/'star-grouped'/f'candidate-{cid:03d}'
    files=sorted((current/'design').glob('*.txt'));assert len(files)==100
    for f in files:
        a=f.read_text().split('\nstderr ')[0]
        b=(original/'design'/f.name).read_text().split('\nstderr ')[0]
        assert a==b,(cid,f.name)
    shared.append(row)
assert len(shared)==5
print('Identical baseline artifacts: 5 x 100',flush=True)
paths=[str(h/'star-grouped'/f'candidate-{i:03d}') for i in range(2000,2004)]
subprocess.run([sys.executable,str(h/'replay_batch.py'),'diagnostic-star-new',*paths,
                '--seeds','0-100'],check=True)
table=shared+json.loads((h/'diagnostic-star-new.json').read_text())
(h/'diagnostic-star.json').write_text(json.dumps(table,indent=2)+'\n')
with (h/'diagnostic-star-metrics.log').open('w') as f:
    subprocess.run(['flock','-x',str(r/'.lock'),'nice','-n','10',sys.executable,
                    str(h/'diagnostic_metrics.py'),str(h/'diagnostic-star.json'),
                    '--output',str(h/'diagnostic-star-metrics.json')],
                   stdout=f,stderr=subprocess.STDOUT,check=True)
