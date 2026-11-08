"""Collect completed training pilots. Invoke under flock + nice."""
from pathlib import Path
import json, subprocess, sys, re

HERE = Path(__file__).resolve().parent
R = Path('/home/sato/ahc074/runs')
BASE = '20261108-040819_deval-helper-wide'
tags = ['pilot2','pilot-warm','pilot-cool','pilot-joint','pilot-control','pilot-reheat',
        'pilot8','pilot-graph','pilot-cut','pilot-reheat8','pilot-warmhole',
        'pilot-preferred','pilot-soft','pilot-distinct','pilot-long8','pilot-deepmap8','pilot-untrap','pilot-star8']
out = []
for tag in tags:
    table = HERE / (tag+'.json')
    if not table.exists(): continue
    ids = re.findall(r'run-id: (\S+)', (HERE/(tag+'.log')).read_text())
    for row in json.loads(table.read_text()):
        normal, replay = Path(row['source']).name, row['replay']
        assert normal in ids
        assert json.loads((R/normal/'meta.json').read_text())['status']=='ok'
        assert json.loads((R/replay/'meta.json').read_text())['status']=='ok'
        metrics = {}
        for label, base, target in [('normal',ids[0],normal),('replay',BASE,replay)]:
            raw = subprocess.check_output([sys.executable,str(HERE/'analyze.py'),base,target],text=True)
            metrics[label] = json.loads(raw)[target]
        out.append({'tag':tag,'source':normal,'replay_run':replay,**metrics})
        d = metrics['replay']['score']['fresh']
        t = metrics['normal']['stage']['helper_end_sec']['mean']
        print(f'{normal:49s} {d["moves"]:+.5f} ±{d["moves_se"]:.5f} moves; {d["pct"]:+.4f} ±{d["pct_se"]:.4f}%; design {t:.4f}s',flush=True)
(HERE/'pilot-consolidated.json').write_text(json.dumps(out,indent=2)+'\n')
