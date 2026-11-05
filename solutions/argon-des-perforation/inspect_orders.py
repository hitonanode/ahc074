"""Use observe.py on the first unequal-cost orders of a changed singleton."""
import json,subprocess,sys
from pathlib import Path
here=Path(__file__).resolve().parent;root=here.parents[1]
sys.path.insert(0,str(root/'scripts'));import replay
seed=296;inp=replay.load_input(seed)
runs=['20261105-233306_esw-slim','20261105-233306_argon-des-perforation']
out=[replay.parse_output(inp,(Path('/home/sato/ahc074/runs')/r/'out'/f'{seed:04d}.txt').read_text())for r in runs]
different=[q for q,(a,b)in enumerate(zip(out[0].queries,out[1].queries))if len(a)!=len(b)]
with (here/'hurt-queries.txt').open('w')as f:
    for q in different[:3]:
        for run in runs:
            subprocess.run([sys.executable,str(root/'scripts/observe.py'),'queries',run,str(seed),
                            '--from',str(q),'--to',str(q+1),'--attr','role,col'],stdout=f,check=True)
