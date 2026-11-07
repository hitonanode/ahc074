"""Build the frozen one-file submission under the shared evaluation lock."""
from pathlib import Path
import sys,subprocess,json,hashlib
root=Path(__file__).resolve().parents[2];p=root/'solutions'/sys.argv[1];source=p/'main.cpp';out=[]
for cc in ['g++','clang++']:
 log=p/('submission-'+cc.replace('+','p')+'.log');binary=p/('submission-'+cc.replace('+','p'))
 cmd=['flock','-x','/home/sato/ahc074/runs/.lock',cc,'-std=c++23','-O2',str(source),'-o',str(binary)]
 with log.open('w') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
 out.append({'compiler':cc,'version':subprocess.check_output([cc,'--version'],text=True).splitlines()[0],'command':cmd,'returncode':r.returncode,'log':log.name,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest()})
 assert r.returncode==0,log
 # Build validation only; actual solver executions always go through pahcer_run.py.
 binary.unlink()
(p/'builds.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
