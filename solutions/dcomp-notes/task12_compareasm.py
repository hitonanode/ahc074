from pathlib import Path
import subprocess,re,json,difflib
R=Path('/home/sato/ahc074/runs');N=Path(__file__).resolve().parent
names=['20261108-204122_dcomp-combo-alt1','20261108-204122_dcomp-combo-dual25']
def get(run):
 bin=R/run/'a.out';syms=[]
 for l in subprocess.check_output(['nm','-S','--defined-only',str(bin)],text=True).splitlines():
  z=l.split()
  if len(z)==4 and 'assign_windows' in z[-1] and not z[-1].endswith('.cold'):syms.append(z[-1])
 out={}
 for name in syms:
  raw=subprocess.check_output(['objdump','-d','--no-show-raw-insn','--disassemble='+name,str(bin)],text=True)
  code=[]
  for l in raw.splitlines():
   m=re.match(r'\s*[0-9a-f]+:\s+(.*)',l)
   if not m:continue
   l=m[1];l=re.sub(r'\b[0-9a-f]+ <','ADDR <',l)
   l=re.sub(r'[-+]?0x[0-9a-f]+\(%rip\)','REL(%rip)',l)
   l=re.sub(r'#\s+[0-9a-f]+', '# ADDR',l)
   l=re.sub(r'\s+',' ',l).strip()
   code.append(l)
  out[name]=code
 return out
a,b=map(get,names);results=[]
for name in a:
 if name not in b:continue
 same=a[name]==b[name];diff=list(difflib.unified_diff(a[name],b[name],n=1))
 results.append({'symbol':name,'a_instructions':len(a[name]),'b_instructions':len(b[name]),'normalized_equal':same,'differences':diff[:150]})
 print(name[:150],len(a[name]),len(b[name]),same)
 if not same:print('\n'.join(diff[:18]))
(N/'t12-asm-diff.json').write_text(json.dumps(results,indent=2)+'\n')
