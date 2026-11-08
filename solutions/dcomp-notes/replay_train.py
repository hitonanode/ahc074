"""Dependent screening replays, through the standard runner; requests are fixed."""
from pathlib import Path
import json, subprocess, sys, time
ROOT=Path(__file__).resolve().parents[2];R=Path('/home/sato/ahc074/runs')
for tag,run in [('unstall','20261108-103125_dcomp-unstall'),('two-anneals','20261108-103318_dcomp-two-anneals'),('two-maps','20261108-103318_dcomp-two-maps')]:
    while True:
        try:
            m=json.loads((R/run/'meta.json').read_text())
            if m['status']=='ok':
                cases=json.loads((R/run/'result.json').read_text())['cases']
                assert len(cases)==500 and all(c['score']>0 for c in cases)
                break
            assert m['status'] not in ('failed','error'),m
        except FileNotFoundError:pass
        time.sleep(10)
    with (ROOT/f'solutions/dcomp-notes/{tag}-replay.log').open('w') as log:
        subprocess.run([sys.executable,str(ROOT/'solutions/dcomp-notes/run.py'),'solutions/legal-tie-fast','--design-from',run,'--orders','8','--seeds','0-500','-c',f'Task8 train replay {tag}; fixed legal-tie-fast request policy; lists1-7 unseen'],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
