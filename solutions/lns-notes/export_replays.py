"""Replay saved candidate artifacts using the unchanged standard request policy."""
from pathlib import Path
import argparse, json, subprocess, sys, time

H=Path(__file__).resolve().parent;R=Path('/home/sato/ahc074/runs')
p=argparse.ArgumentParser();p.add_argument('tag');p.add_argument('--source',required=True)
p.add_argument('--directory',required=True);p.add_argument('--ids',required=True)
p.add_argument('--seeds',default='0-100');a=p.parse_args()
while True:
    m=json.loads((R/a.source/'meta.json').read_text())
    if m['status']=='ok':break
    assert m['status'] not in ['error','failed','compile_error'],m['status']
    time.sleep(10)
subprocess.run([sys.executable,str(H/'prepare_artifacts.py'),a.directory,'--source',a.source],check=True)
paths=[str(Path(a.directory).resolve()/f'candidate-{int(i):03d}') for i in a.ids.split(',')]
subprocess.run([sys.executable,str(H/'replay_batch.py'),a.tag,*paths,'--seeds',a.seeds],check=True)
with (H/(a.tag+'-metrics.log')).open('w') as f:
    subprocess.run(['flock','-x','/home/sato/ahc074/runs/.lock','nice','-n','10',sys.executable,
                    str(H/'diagnostic_metrics.py'),str(H/(a.tag+'.json')),'--output',str(H/(a.tag+'-metrics.json'))],
                   stdout=f,stderr=subprocess.STDOUT,check=True)
