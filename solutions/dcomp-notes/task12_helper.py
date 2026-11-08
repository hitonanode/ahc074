from pathlib import Path
import json,numpy as np
R=Path('/home/sato/ahc074/runs');N=Path(__file__).resolve().parent
pairs=[('fastgcc','20261108-200928_dcomp-combo-alt1','20261108-200928_dcomp-t11-fast-late',500),('dual','20261108-204122_dcomp-combo-alt1','20261108-204122_dcomp-combo-dual25',500),('fastnative','20261108-202247_dcomp-combo-alt1','20261108-202247_dcomp-t11-fast-late',200),('fastclang','20261108-201528_dcomp-combo-alt1','20261108-201528_dcomp-t11-fast-late',500)]
out={}
for label,b,c,count in pairs:
 def read(rid):
  d=json.loads((R/rid/'metrics.json').read_text())['cases'];return [d[str(i)]['stderr'] if str(i) in d else d[f'{i:04d}']['stderr'] for i in range(count)]
 br,cr=read(b),read(c);ks=sorted(set(br[0])&set(cr[0]));v={}
 for k in ks:
  if k.endswith('_sec') and all(k in r for r in br+cr):
   x=np.array([r[k] for r in cr])-np.array([r[k] for r in br]);v[k]={'delta_ms':float(1000*x.mean()),'se_ms':float(1000*x.std(ddof=1)/np.sqrt(count))}
 out[label]={'reference':b,'candidate':c,'n':count,'metrics':v};print(label,v,flush=True)
(N/'t12-helper-old.json').write_text(json.dumps(out,indent=2)+'\n')
