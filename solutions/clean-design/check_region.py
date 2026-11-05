"""Reject any change to the other session's regions or the shared header/Common."""
import re,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
BASE=HERE.parents[1]/'solutions/time-alloc/main.cpp'
def sections(s):
    pat=re.compile(r'^\s*// ==== (.*?) ====\s*$',re.M)
    ms=list(pat.finditer(s));out={'header':s[:ms[0].start()]}
    for i,m in enumerate(ms):out[m[1]]=s[m.start():ms[i+1].start() if i+1<len(ms) else len(s)]
    return out
prefixes=('Generic layer:', 'Window assignment:', 'Design:', 'Design annealing', 'Filler climb:',
          'Head-aware reassignment', 'Helper tables:', 'Emergency design', 'Handle perforation',
          'Design state:', 'Design iteration counts', 'design_papers:', 'Saving and loading',
          'Analysis output (LOCAL_BENCH): paper attributes', 'main: input', 'main: the design',
          'main: helper tables', 'main: simulation harness', 'main: output of the papers')
candidate=Path(sys.argv[1]) if len(sys.argv)>1 else HERE/'main.cpp'
b=sections(BASE.read_text());after=sections(candidate.read_text())
assert all(k in after for k in b),'original section removed/renamed'
assert all(k in b or k.startswith(prefixes) for k in after),'unowned section added'
old=new=0
for k,v in b.items():
    if k.startswith(prefixes):old+=len(v.splitlines())
    else:assert v==after[k],f'out-of-region change: {k}'
new=sum(len(v.splitlines()) for k,v in after.items() if k.startswith(prefixes))
print(f'Allowed region: {old} -> {new} lines; all other sections byte-identical')
