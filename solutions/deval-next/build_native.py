from pathlib import Path
import sys,subprocess,json,hashlib
p=Path(__file__).resolve().parents[2]/'solutions'/sys.argv[1];source=p/'main.cpp';out=[]
for cc in ['g++','clang++']:
 tag=cc.replace('+','p');log=p/f'submission-native-{tag}.log';binary=p/f'submission-native-{tag}'
 cmd=['flock','-x','/home/sato/ahc074/runs/.lock',cc,'-std=c++23','-O2','-march=native',str(source),'-o',str(binary)]
 with log.open('w') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
 assert r.returncode==0,log
 out.append({'compiler':cc,'command':cmd,'returncode':r.returncode,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'log':log.name});binary.unlink()
(p/'builds-native.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
