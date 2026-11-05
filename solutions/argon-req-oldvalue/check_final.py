from pathlib import Path
import sys,re,hashlib
base_run,cand_run,fixed_run,solution=sys.argv[1:]
root=Path('/home/sato/ahc074/runs');base=root/base_run;cand=root/cand_run;fixed=root/fixed_run
ignored={'value_filler_zero','value_filler_zero_useful'}
count=0;metric=re.compile(r'^(\w+) = [-+\d.eE]+$',re.M)
for f in sorted((base/'out').glob('*.txt')):
 other=cand/'out'/f.name
 a=f.read_text().splitlines();b=other.read_text().splitlines()
 assert a[:192]==b[:192],('design stdout',f.name)
 assert other.read_bytes()==(fixed/'out'/f.name).read_bytes(),('fixed-normal stdout',f.name)
 aa=(base/'err'/f.name).read_text();bb=(cand/'err'/f.name).read_text()
 assert [s for s in aa.splitlines() if s.startswith('@paper')]==[s for s in bb.splitlines() if s.startswith('@paper')],('paper attrs',f.name)
 aks=[k for k in metric.findall(aa) if k not in ignored]
 bks=[k for k in metric.findall(bb) if k in set(aks)]
 assert aks==bks,('metric names/order',f.name,set(aks)-set(bks))
 count+=1
print('design stdout / @paper / fixed-normal stdout / existing metric names+order:',count,'passed')
assert count==2000
source=Path(solution)/'main.cpp';body=source.read_bytes();digest=hashlib.sha256(body).hexdigest()
evaluated=(cand/'src/main.cpp').read_bytes()
assert evaluated==(fixed/'src/main.cpp').read_bytes()
assert [x.strip() for x in body.splitlines()]==[x.strip() for x in evaluated.splitlines()]
print('evaluated SHA256',hashlib.sha256(evaluated).hexdigest(),'; byte-identical current source' if body==evaluated else '; indentation-only difference, with identical line numbers')
print('source SHA256',digest)
basebody=(base/'src/main.cpp').read_text();text=body.decode()
markers=lambda t:re.findall(r'^\s*// ==== .+ ====$',t,re.M)
assert markers(basebody)==markers(text)
toc=lambda t:re.findall(r'^//   .+$',t,re.M)
assert toc(basebody)==toc(text)
print('section markers and TOC unchanged; lines',len(basebody.splitlines()),'->',len(text.splitlines()))
# Source regions outside request processing are exact copies of the current base.
def parts(t):
 ms=list(re.finditer(r'^\s*// ==== (.+) ====$',t,re.M))
 return {m.group(1):t[m.end():ms[i+1].start() if i+1<len(ms) else len(t)] for i,m in enumerate(ms)}
a=parts(basebody);b=parts(text)
changed=[name for name in a if a[name]!=b[name]]
print('changed sections',changed)
assert all(name.startswith(('Request plans:','Request processing','Solver:','Post-processing:','main: statistics')) for name in changed)
for run in [base,cand]:print('saved design files',run.name,len(list((run/'design').glob('*'))))
