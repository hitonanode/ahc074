"""研究用バイナリを work/ に再構築する。既存・提出用ソースは変更しない。"""
from pathlib import Path
import subprocess,os,sys
r=Path(__file__).resolve().parent;(r/'work').mkdir(exist_ok=True)
env=os.environ.copy();env['TMPDIR']=str(r/'work')
subprocess.run([sys.executable,str(r/'build_grid.py')],env=env,check=True)
jobs=[('base',r.parent/'as6-cap38/main.cpp',[]),('repair',r/'repair.cpp',[]),('repair-plus',r/'repair_plus.cpp',[]),('mapcap',r/'mapcap.cpp',[]),('mapcap2',r/'mapcap2.cpp',[]),('combo',r/'combo.cpp',[]),('select2',r/'select.cpp',[]),('spare',r/'spare.cpp',[]),('color',r/'color.cpp',[]),('m5c1g34',r/'five.cpp',['-DCAP_COUNT=1','-DGENERIC_COUNT=34']),('m5c2g33',r/'five.cpp',['-DCAP_COUNT=2','-DGENERIC_COUNT=33']),('cause_probe',r/'cause_probe.cpp',[]),('shared_cap_model',r/'shared_cap_model.cpp',[]),('sparse_mapping',r/'sparse_mapping.cpp',[])]
for name,src,flags in jobs:
 subprocess.run(['g++','-std=c++23','-O2','-DCLOCK_SCALE=1.1',*flags,str(src),'-o',str(r/'work'/name)],env=env,check=True)
 print(name,flush=True)
