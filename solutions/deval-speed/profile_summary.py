from pathlib import Path
import json,sys
import numpy as np
run=sys.argv[1]
cases=json.loads((Path('/home/sato/ahc074/runs')/run/'metrics.json').read_text())['cases']
rows=[c['stderr'] for c in cases.values()]
means={k:float(np.mean([x[k] for x in rows if k in x])) for k in rows[0]}
for prefix,suffix in [('cfprof_','_exc'),('cfprof_','_inc'),('af_','_sec')]:
    print(prefix,suffix)
    for k in sorted((k for k in means if k.startswith(prefix) and k.endswith(suffix)),key=means.get,reverse=True):
        print(k,round(means[k],6))
Path(__file__).with_name('profile.json').write_text(json.dumps(means,indent=2)+'\n')
