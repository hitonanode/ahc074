"""Compile, but do not execute, the frozen submission with GCC and Clang C++23."""
from pathlib import Path
import subprocess,sys,json,hashlib
S=Path(sys.argv[1]).resolve()
source=S/'main.cpp'
freeze=json.loads((S/'FROZEN.json').read_text())
assert hashlib.sha256(source.read_bytes()).hexdigest()==freeze['sha256']
records=[]
for compiler,tag in [('g++','gcc'),('clang++','clang')]:
    cmd=['flock','-x','/home/sato/ahc074/runs/.lock',compiler,'-std=c++23','-O2',str(source),'-o',str(S/('submission-'+tag))]
    with (S/('build-'+tag+'.log')).open('w') as f:
        p=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
    records.append({'compiler':compiler,'version':subprocess.check_output([compiler,'--version'],text=True).splitlines()[0],'command':cmd,'exit_code':p.returncode,'LOCAL_BENCH':False,'source_sha256':freeze['sha256']})
    (S/'builds.json').write_text(json.dumps(records,indent=2)+'\n')
    assert p.returncode==0,(compiler,p.returncode)
    print(compiler,'submission build OK',flush=True)
