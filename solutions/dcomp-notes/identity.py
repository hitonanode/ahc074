"""Byte identity of normal output files; run under flock + nice."""
from pathlib import Path
import argparse,json
p=argparse.ArgumentParser();p.add_argument('a');p.add_argument('b');p.add_argument('--output');x=p.parse_args()
R=Path('/home/sato/ahc074/runs');a,b=R/x.a,R/x.b
for d in [a,b]:assert json.loads((d/'meta.json').read_text())['status']=='ok'
fs=sorted(f for f in (a/'out').glob('*.txt') if (b/'out'/f.name).exists());assert len(fs)>=200
different=[f.name for f in fs if f.read_bytes()!=(b/'out'/f.name).read_bytes()]
s=json.dumps({'a':a.name,'b':b.name,'n':len(fs),'identical':len(fs)-len(different),'different':different})
if x.output:Path(x.output).write_text(s+'\n')
print(s);raise SystemExit(bool(different))
