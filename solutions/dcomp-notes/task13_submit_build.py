"""Submission builds only, locked and nice; never execute a binary directly."""
from pathlib import Path
import subprocess,json,hashlib
N=Path(__file__).resolve().parent;R=N.parents[1];src=R/'solutions/dcomp-time-target/main.cpp'
freeze=json.loads((N/'t13-freeze.json').read_text());sha=hashlib.sha256(src.read_bytes()).hexdigest();assert sha==freeze['dcomp-time-target']
tmp=Path('/tmp/ahc074-task13-build');tmp.mkdir(exist_ok=True);out={}
for label,cxx,extra in [('gcc','g++',[]),('clang','clang++',[]),('clang-libcxx-zero','clang++',['-stdlib=libc++','-ftrivial-auto-var-init=zero'])]:
 cmd=['flock','-x','/home/sato/ahc074/runs/.lock','nice','-n','10',cxx,'-std=c++23','-O2','-march=native',*extra,str(src),'-o',str(tmp/label)]
 with (N/f't13-submit-{label}.log').open('w')as f:subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,check=True)
 out[label]={'command':cmd,'compiler':subprocess.check_output([cxx,'--version'],text=True).splitlines()[0]}
 assert hashlib.sha256(src.read_bytes()).hexdigest()==sha
(N/'t13-submission-builds.json').write_text(json.dumps({'sha256':sha,'builds':out},indent=2)+'\n')
print('all submission builds succeeded')
