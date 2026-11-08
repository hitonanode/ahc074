from pathlib import Path
import subprocess,json,re
R=Path('/home/sato/ahc074/runs');N=Path(__file__).resolve().parent
rs=['20261108-204122_dcomp-combo-alt1','20261108-204122_dcomp-combo-dual25','20261108-200928_dcomp-t11-fast-late']
out={}
for r in rs:
 syms=[]
 for ln in subprocess.check_output(['nm','-S','--defined-only',str(R/r/'a.out')],text=True).splitlines():
  z=ln.split()
  if len(z)!=4:continue
  addr,size,kind,name=z
  if 'assign_windows' in name or 'Design6anneal' in name:
   if name.endswith('.cold'):continue
   syms.append({'name':name,'address':int(addr,16),'mod64':int(addr,16)%64,'size':int(size,16)})
 out[r]=syms
 print(r,[(z['name'][:95],z['size'],z['mod64']) for z in syms],flush=True)
(N/'t12-asm-symbols.json').write_text(json.dumps(out,indent=2)+'\n')
