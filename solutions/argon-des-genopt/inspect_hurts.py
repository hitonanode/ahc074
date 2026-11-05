"""Small observe.py excerpts for cases where the D1 prediction did not materialize."""
import subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent
BASE='20261105-225223_esw-slim';CAND='20261105-225236_argon-des-genopt'
commands=[['cases',CAND,'--vs',BASE]]
for run in [BASE,CAND]:
    commands.append(['queries',run,'40','--from','850','--to','855','--attr','role,col'])
    commands.append(['queries',run,'48','--from','175','--to','180','--attr','role,col'])
with (HERE/'hurt-queries.txt').open('w')as f:
    for args in commands:
        f.write('COMMAND: scripts/observe.py '+' '.join(args)+'\n')
        p=subprocess.run(['python3','scripts/observe.py',*args],capture_output=True,text=True,check=True)
        f.write(p.stdout+p.stderr+'\n')
