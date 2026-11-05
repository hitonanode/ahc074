"""Summarize completed D2 experiments sequentially while holding the idle lock."""
from pathlib import Path
import subprocess,sys
here=Path(__file__).resolve().parent
groups=[
 ('headmix-500',['20261105-233934_esw-slim','20261105-234020_argon-des-headmix']),
 ('dense-500',['20261105-234103_esw-slim','20261105-234230_argon-des-perf-dense']),
 ('pairs-100',['20261105-234359_esw-slim','20261105-234412_argon-des-perf-pairs']),
]
for name,runs in groups:
    with (here/(name+'-summary.log')).open('w')as out:
        subprocess.run([sys.executable,str(here/'summarize.py'),*runs,'--output',name+'.json'],stdout=out,check=True)
    print('summarized',name,flush=True)
