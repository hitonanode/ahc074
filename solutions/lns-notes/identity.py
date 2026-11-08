from pathlib import Path
import sys,json
R=Path('/home/sato/ahc074/runs');a,b=map(lambda s:R/s,sys.argv[1:3])
for d in [a,b]:assert json.loads((d/'meta.json').read_text())['status']=='ok'
fs=sorted((a/'out').glob('*.txt'));different=[f.name for f in fs if f.read_bytes()!=(b/'out'/f.name).read_bytes()]
print(json.dumps({'a':a.name,'b':b.name,'n':len(fs),'identical':len(fs)-len(different),'different':different}))
raise SystemExit(bool(different))
