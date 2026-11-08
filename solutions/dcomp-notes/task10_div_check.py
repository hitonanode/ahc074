"""Independent numeric analysis. Call under the evaluation lock and nice."""
from pathlib import Path
import subprocess,json
root=Path(__file__).resolve().parents[2];scratch=Path('/tmp/dcomp-task10-math');scratch.mkdir(exist_ok=True)
result={}
for compiler in ['g++','clang++']:
 out=scratch/('check-'+compiler.replace('+','p'))
 cmd=[compiler,'-O2','-std=c++23','-march=native',str(root/'solutions/dcomp-notes/task10_div_check.cpp'),'-o',str(out)]
 subprocess.run(cmd,check=True);p=subprocess.run([str(out)],capture_output=True,text=True)
 result[compiler]={'command':cmd,'returncode':p.returncode,'output':p.stdout+p.stderr}
 print(compiler,p.stdout)
(root/'solutions/dcomp-notes/t10-division-check.json').write_text(json.dumps(result,indent=2)+'\n')
assert all(x['returncode']==0 for x in result.values())
