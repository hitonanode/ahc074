"""Repeat diagnostic replays after fixing absolute artifact path preservation.

Never reuse the earlier zero-score replays. Frozen solver sources are untouched.
"""
from pathlib import Path
import json,re,subprocess,sys,time

h=Path(__file__).resolve().parent;r=Path('/home/sato/ahc074/runs')
log=h/'artifact-smoke.log'
while True:
    ids=re.findall(r'run-id: (\S+)',log.read_text()) if log.exists() else []
    if ids:
        m=json.loads((r/ids[0]/'meta.json').read_text())
        if m['status']=='ok':break
        assert m['status'] not in ['compile_error','error','failed']
    time.sleep(10)
smoke=ids[0]
cases=json.loads((r/smoke/'result.json').read_text())['cases']
assert len(cases)==4 and all(min(c['order_scores'])>0 for c in cases)
base={c['seed']:c for c in json.loads((r/'20261108-040819_deval-helper-wide/result.json').read_text())['cases']}
assert all(c['order_scores']==base[c['seed']]['order_scores'][:2] for c in cases)
(h/'artifact-smoke-check.json').write_text(json.dumps({'run':smoke,'cases':4,'orders':2,'all_positive':True,'scores_match_SOTA':True},indent=2)+'\n')
print('Artifact smoke passed, scores match SOTA:',smoke,flush=True)

def replay(tag,paths):
    with (h/(tag+'.log')).open('w') as f:
        subprocess.run([sys.executable,str(h/'replay_batch.py'),tag,*map(str,paths),
                        '--seeds','0-100'],stdout=f,stderr=subprocess.STDOUT,check=True)
    return json.loads((h/(tag+'.json')).read_text())

def metrics(tag):
    with (h/(tag+'-metrics.log')).open('w') as f:
        subprocess.run(['flock','-x',str(r/'.lock'),'nice','-n','10',sys.executable,
                        str(h/'diagnostic_metrics.py'),str(h/(tag+'.json')),
                        '--output',str(h/(tag+'-metrics.json'))],
                       stdout=f,stderr=subprocess.STDOUT,check=True)
    print(tag,'metrics complete',flush=True)

ids=[0,1,2,3,1000,2000,2001,2002,2003,3000,4000,5000]
joint=replay('diagnostic-joint-fixed',[h/'pilot8-dump/lns-joint-study'/f'candidate-{i:03d}' for i in ids])
metrics('diagnostic-joint-fixed')
star=replay('diagnostic-star-fixed-new',[h/'star-grouped'/f'candidate-{i:03d}' for i in range(2000,2004)])
shared=[row for row in joint if json.loads((Path(row['source'])/'meta.json').read_text())['candidate_id'] in [0,1,2,3,1000]]
assert len(shared)==5
(h/'diagnostic-star-fixed.json').write_text(json.dumps(shared+star,indent=2)+'\n')
metrics('diagnostic-star-fixed')
