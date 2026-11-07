import json,sys
from pathlib import Path
m=json.loads((Path('/home/sato/ahc074/runs')/sys.argv[1]/'metrics.json').read_text())['cases']
a=[x['stderr'] for x in m.values()]
for p,suf in [('cfprof_','_exc'),('cfprof_','_inc'),('af_','_sec'),('dprof_','_mcyc')]:
 out={k:sum(x.get(k,0) for x in a)/len(a) for k in a[0] if k.startswith(p) and k.endswith(suf)}
 print(p)
 for k,v in sorted(out.items(),key=lambda z:-z[1])[:30]:print(k,round(v,6))
