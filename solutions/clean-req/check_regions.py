from pathlib import Path
import re,json,sys
pattern=re.compile(r'^\s*// ==== (.*?) ====\s*$',re.M)
def sections(path):
 s=Path(path).read_text();m=list(pattern.finditer(s))
 return {'header':s[:m[0].start()],**{x[1]:s[x.start():m[i+1].start() if i+1<len(m) else len(s)] for i,x in enumerate(m)}}
def allowed(name):
 return name.startswith(('Solver:', 'Request plans:', 'Post-processing:')) or name in ['Request profiling (COLFAST_PROFILE): inclusive and exclusive times','Analysis output (LOCAL_BENCH): move labels','Column MDP: long-run values of the order of a column','Request processing (process)','main: requests','main: statistics']
a=sections('solutions/time-alloc/main.cpp');b=sections(sys.argv[1] if len(sys.argv)>1 else 'solutions/clean-req/main.cpp')
assert a.keys()==b.keys(),'Section names changed'
for k in a:
 if not allowed(k):assert a[k]==b[k],k
print('Only assigned sections changed.')
print('region lines',sum(len(v.splitlines()) for k,v in a.items() if allowed(k)),'->',sum(len(v.splitlines()) for k,v in b.items() if allowed(k)))
