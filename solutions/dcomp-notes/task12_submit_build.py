"""Build frozen submission flags on both compilers; never execute the binaries."""
from pathlib import Path
import subprocess,hashlib,json
N=Path(__file__).resolve().parent;R=N.parents[1]
f=json.loads((N/'t12-final-freeze.json').read_text());name=f['candidate'];src=R/'solutions'/name/'main.cpp'
sha=hashlib.sha256(src.read_bytes()).hexdigest();assert sha==f['hashes'][name]
scratch=Path('/tmp/ahc074-task12-submit');scratch.mkdir(exist_ok=True);out={}
for label,cxx in [('gcc','g++'),('clang','clang++')]:
 cmd=['flock','-x','/home/sato/ahc074/runs/.lock','nice','-n','10',cxx,'-std=c++23','-O2','-march=native',str(src),'-o',str(scratch/(name+'-'+label))]
 with (N/('t12-submit-'+label+'.log')).open('w')as log:subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,check=True)
 out[label]={'command':cmd,'compiler':subprocess.check_output([cxx,'--version'],text=True).splitlines()[0],'binary':str(scratch/(name+'-'+label))}
 assert hashlib.sha256(src.read_bytes()).hexdigest()==sha
(N/'t12-submit-build.json').write_text(json.dumps({'source_sha256':sha,'builds':out},indent=2)+'\n')
print('both submission builds succeeded')
