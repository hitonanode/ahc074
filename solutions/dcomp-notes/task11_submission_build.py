"""Compile the frozen submission source without LOCAL_BENCH; never execute it.
Invoke under the shared flock and nice. Binary outputs stay in /tmp.
"""
from pathlib import Path
import hashlib,json,subprocess,tempfile
N=Path(__file__).resolve().parent;R=N.parents[1]
f=json.loads((N/'t11-final-freeze.json').read_text());name=f['candidate'];src=R/'solutions'/name/'main.cpp'
assert hashlib.sha256(src.read_bytes()).hexdigest()==f['hashes'][name]
scratch=Path(tempfile.mkdtemp(prefix='dcomp-task11-submission-',dir='/tmp'));result={}
for compiler in ['g++','clang++']:
 target=scratch/('solver-gcc' if compiler=='g++' else 'solver-clang')
 cmd=[compiler,'-std=c++23','-O2','-march=native','-o',str(target),str(src)]
 v=subprocess.run(cmd,text=True,capture_output=True)
 result[compiler]={'command':cmd,'returncode':v.returncode,'stdout':v.stdout,'stderr':v.stderr,
                   'version':subprocess.check_output([compiler,'--version'],text=True).splitlines()[0]}
 assert v.returncode==0,(compiler,v.stderr)
result['source_sha256']=hashlib.sha256(src.read_bytes()).hexdigest()
(N/'t11-submission-build.json').write_text(json.dumps(result,indent=2)+'\n')
print('Submission compile passed for GCC and Clang:',name,flush=True)
