#!/usr/bin/env python3
"""H=32/36 の経路を診断コピーで照合する。提出ソースは変えない。"""
from pathlib import Path
import subprocess
import sys
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
for g in (32,28):
    names=[]
    for name,path in [('base',ROOT/'solutions/astra-assign/main.cpp'),('main',HERE/'main.cpp')]:
        stem=f'g{g}-{name}'
        source=HERE/(stem+'.cpp')
        text=path.read_text()
        assert 'int M = 6, G = 36;' in text
        source.write_text(text.replace('int M = 6, G = 36;',f'int M = 6, G = {g};'))
        subprocess.run(['g++','-std=c++23','-O2','-DCLOCK_SCALE=1.1',str(source),'-o',str(HERE/stem)],check=True)
        names.append(stem)
    subprocess.run([sys.executable,str(HERE/'measure.py'),'--binaries',*names,'--seeds','0,3','--repeats','1','--label',f'modes-g{g}','--check'],check=True)
