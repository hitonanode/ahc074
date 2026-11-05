import json,math,statistics
from pathlib import Path
root=Path('/home/sato/ahc074/runs');here=Path(__file__).resolve().parent
r=[json.loads((root/n/'metrics.json').read_text())['cases']for n in ['20261106-065002_argon-des-perf-modelprobe','20261106-065003_argon-des-perf-modelprobe']]
out=[]
for model in ['sum','interval','one']:
 for w in [.5,.7,.85,1,1.05]:
  for threshold in [0,-.001,-.002]:
   values=[];chosen=0
   for s,a in r[0].items():
    b=r[1][s];ea,eb=a['stderr'],b['stderr']
    d=eb['d2_probe_hole']-ea['d2_probe_hole']-w*(eb['d2_probe_'+model]-ea['d2_probe_'+model])
    take=d<threshold-1e-8;chosen+=take
    values.append(100*math.log(b['score']/a['score'])if take else 0)
   out.append(dict(model=model,weight=w,threshold=threshold,chosen=chosen,diff=statistics.mean(values),se=statistics.stdev(values)/math.sqrt(len(values))))
(here/'gate-diagnosis.json').write_text(json.dumps(out,indent=2)+'\n')
for x in out:print(x)
