"""Descriptive held-out diagnostics for the already-frozen sources; no fitting."""
from pathlib import Path
import hashlib, json, os, subprocess, sys, time

h=Path(__file__).resolve().parent;root=h.parents[1]
while True:
    p=h/'heldout-runs.json'
    if p.exists():
        rows=json.loads(p.read_text())
        if len(rows)==3:break
    time.sleep(10)
record=next(x for x in rows if x['budget']==8)
frozen=json.loads((h/'heldout-frozen.json').read_text())
for name,digest in frozen['sha256'].items():
    assert hashlib.sha256((root/'solutions'/name/'main.cpp').read_bytes()).hexdigest()==digest
mapping={name:(normal,replay) for name,normal,replay in
         zip(record['solvers'],record['normal'][1:],record['replays'])}

def locked(script,args,tag):
    with (h/(tag+'.log')).open('w') as f:
        subprocess.run(['flock','-x','/home/sato/ahc074/runs/.lock','nice','-n','10',
                        sys.executable,str(h/script),*args,'--output',str(h/(tag+'.json'))],
                       cwd=root,stdout=f,stderr=subprocess.STDOUT,check=True)
    print(tag,'done',flush=True)

locked('source_audit.py',record['solvers'],'final-source-audit')
for name,(normal,replay) in mapping.items():
    locked('winning_changes.py',[record['baseline'],replay,
          '--base-design','20261107-165305_deval-flex125-plan3',
          '--candidate-design',normal],'final-'+name+'-structure')
star=mapping['lns-star-study'][1];control=mapping['lns-full-study'][1]
locked('label_changes.py',[record['baseline'],star],'final-star-labels-vs-base')
locked('label_changes.py',[control,star],'final-star-labels-vs-control')
