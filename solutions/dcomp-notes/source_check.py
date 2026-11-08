"""Read-only request-policy equivalence and frozen-source integrity checks."""
from pathlib import Path
import argparse,hashlib,json
p=argparse.ArgumentParser();p.add_argument('candidate');p.add_argument('--output',required=True);a=p.parse_args()
r=Path(__file__).resolve().parents[2]
base=(r/'solutions/legal-tie-fast/main.cpp').read_text();s=(r/'solutions'/a.candidate/'main.cpp').read_text()
blocks=[('// ==== Helper tables: dedicated papers inside the generic layer (Interleave) ====','// ==== Emergency design ===='),('// ==== main: helper tables and the generic look-ahead ==== ',None)]
checks={}
for start,end in [(blocks[0][0],blocks[0][1]),('// ==== main: helper tables and the generic look-ahead ====',None)]:
 def section(t):
  i=t.index(start);return t[i:t.index(end,i)] if end else t[i:]
 x,y=section(base),section(s);assert x==y,start
 checks[start]=hashlib.sha256(x.encode()).hexdigest()
out={'candidate':a.candidate,'source_sha256':hashlib.sha256(s.encode()).hexdigest(),'source_bytes':len(s.encode()),'request_policy':'legal-tie-fast','request_blocks_identical':checks}
Path(a.output).write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
