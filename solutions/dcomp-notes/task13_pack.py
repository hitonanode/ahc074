"""Produce design-only patches and verify a three-way port onto dual25."""
from pathlib import Path
import hashlib,difflib,json,subprocess
N=Path(__file__).resolve().parent;R=N.parents[1]
base=R/'solutions/dcomp-combo-dual30/main.cpp';old=base.read_text()
freeze=json.loads((N/'t13-freeze.json').read_text());out={}
first='// ==== Solver: papers, handles and the generic look-ahead ===='
last='// ==== Emergency design ===='
requests='    // ==== main: requests ===='
def signature(s):return [s.split(first)[1].split(last)[0],s.split(requests)[1]]
for name in ['same','target']:
 d=R/f'solutions/dcomp-time-{name}';src=d/'main.cpp';new=src.read_text()
 assert hashlib.sha256(src.read_bytes()).hexdigest()==freeze[d.name]
 assert signature(old)==signature(new)
 patch=''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='a/main.cpp',tofile='b/main.cpp'))
 (d/'design.patch').write_text(patch)
 out[name]={'base_sha256':hashlib.sha256(base.read_bytes()).hexdigest(),'sha256':freeze[d.name],
            'patch':str(d/'design.patch'),'request_sections_identical':True}
readme=R/'solutions/dcomp-combo-dual25/main.cpp'
merged=subprocess.run(['git','merge-file','-p',str(readme),str(base),str(R/'solutions/dcomp-time-target/main.cpp')],capture_output=True,text=True)
assert merged.returncode==0,merged.stderr
assert signature(merged.stdout)==signature(readme.read_text())
preview=N/'dual25-time-target.preview.cpp';preview.write_text(merged.stdout)
out['dual25_port']={'clean_three_way_merge':True,'request_sections_identical':True,'preview':str(preview)}
(N/'t13-patch-audit.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2))
