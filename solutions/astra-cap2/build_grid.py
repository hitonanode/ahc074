from pathlib import Path
import subprocess,os
r=Path(__file__).resolve().parent
(r/'work').mkdir(exist_ok=True)
env=os.environ.copy();env['TMPDIR']=str(r/'work')
configs=[('research-c1g38',1,1,1,38),('c2g37',2,2,3,37),('c0g38',0,0,0,38),('c0g39',0,0,0,39),('c1g39',1,1,1,39),('c2g38',2,2,3,38),('c2g36',2,2,3,36),('c2g37mixed',2,2,1,37),('c1w2g37',1,2,3,37),('c3g36',3,3,7,36)]
for name,c,w,color,g in configs:
 cmd=['g++','-std=c++23','-O2','-DCLOCK_SCALE=1.1',f'-DCAP_COUNT={c}',f'-DCAP_WIDTH={w}',f'-DCAP_COLORS={color}',f'-DGENERIC_COUNT={g}',str(r/'research.cpp'),'-o',str(r/'work'/name)]
 subprocess.run(cmd,check=True,env=env)
 print(name,flush=True)
