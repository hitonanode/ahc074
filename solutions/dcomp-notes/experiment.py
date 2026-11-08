"""Recorded normal screening followed by standard, unrecorded design replays."""
from pathlib import Path
import argparse,json,re,subprocess,sys
ROOT=Path(__file__).resolve().parents[2];NOTES=ROOT/'solutions/dcomp-notes';RUNS=Path('/home/sato/ahc074/runs')
p=argparse.ArgumentParser();p.add_argument('tag');p.add_argument('candidates',nargs='+');a=p.parse_args()
def run(args,log):
    with log.open('w') as f:subprocess.run([sys.executable,str(NOTES/'run.py')]+args,cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,check=True)
    ids=re.findall(r'\[pahcer_run\] run-id: (\S+)',log.read_text());assert ids
    for rid in ids:
        m=json.loads((RUNS/rid/'meta.json').read_text());assert m['status']=='ok',(rid,m['status'])
        cases=json.loads((RUNS/rid/'result.json').read_text())['cases'];assert len(cases)==500 and all(c['score']>0 for c in cases)
    return ids
ids=run(['--compare','solutions/legal-tie-fast']+['solutions/'+c for c in a.candidates]+['--seeds','0-500','--save-design','-c',f'Task8 {a.tag}: same-budget design reinvestment; train only'],NOTES/f'{a.tag}-normal.log')
manifest={'normal':ids,'replays':{}}
dest=NOTES/f'{a.tag}-runs.json';dest.write_text(json.dumps(manifest,indent=2)+'\n')
for cand,source in zip(a.candidates,ids[1:]):
    replay=run(['solutions/legal-tie-fast','--design-from',source,'--orders','8','--seeds','0-500','-c',f'Task8 {a.tag} {cand}: train replay with fixed legal-tie-fast requests'],NOTES/f'{a.tag}-{cand}-replay.log')
    manifest['replays'][cand]=replay[0];dest.write_text(json.dumps(manifest,indent=2)+'\n')
    subprocess.run([sys.executable,str(NOTES/'analyze.py'),'20261108-102842_legal-tie-fast',replay[0],'--scores-only','--output',str(NOTES/f'{a.tag}-{cand}-scores.json')],cwd=ROOT,check=True)
