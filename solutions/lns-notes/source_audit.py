"""Verify unchanged request/finishing primitives in selected research sources."""
from pathlib import Path
import argparse, hashlib, json

p=argparse.ArgumentParser()
p.add_argument('solvers', nargs='+')
p.add_argument('--output', required=True)
a=p.parse_args()
root=Path(__file__).resolve().parents[2]
base=(root/'solutions/deval-helper-wide/main.cpp').read_text()
markers=[
 ('design_value', '// ==== V: design-only expected moves ====', '} // namespace deval'),
 ('requests_and_perforation',
  '// ==== Helper tables: dedicated papers inside the generic layer (Interleave) ====',
  '// ==== V: design-only expected moves ===='),
 ('design_store_main_requests',
  '// ==== Saving and loading the design state (LOCAL_BENCH: DesignStore) ====',None),
 ('column_and_rematching_primitives',
  '// ==== Design: units, columns and the cost model ====',
  '// ==== Helper tables: dedicated papers inside the generic layer (Interleave) ====')]

def region(s, start, end):
    s=s[s.index(start):]
    if end is not None:s=s[:s.index(end)]
    # The new repair is inserted between the original Design and Interleave.
    cut='// ==== Large neighborhood: matching and column repair ===='
    if cut in s:s=s[:s.index(cut)]
    return s.rstrip()

out={}
for name in a.solvers:
    assert name.startswith('lns-')
    source=(root/'solutions'/name/'main.cpp').read_text()
    out[name]={}
    for label,start,end in markers:
        x,y=region(base,start,end),region(source,start,end)
        assert x==y,(name,label)
        out[name][label]=hashlib.sha256(y.encode()).hexdigest()
Path(a.output).write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2))
