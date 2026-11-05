#!/usr/bin/env python3
"""Compile the selected source, without executing any test case. Hold runs/.lock externally."""
from pathlib import Path
import subprocess
root=Path(__file__).resolve().parent
for compiler in ['g++','clang++']:
    for bench in [False,True]:
        out=root/('build-'+compiler+('-bench' if bench else '-plain'))
        cmd=[compiler,'-std=c++23','-O2','-Wall','-Wextra']
        if bench:cmd+=['-DLOCAL_BENCH','-DCLOCK_SCALE=1.1']
        cmd+=[str(root/'main.cpp'),'-o',str(out)]
        print(' '.join(cmd),flush=True)
        r=subprocess.run(cmd)
        out.unlink(missing_ok=True)
        if r.returncode:raise SystemExit(r.returncode)
print('All four builds passed.',flush=True)
