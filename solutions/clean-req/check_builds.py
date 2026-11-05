"""Compile only. Run under the shared evaluation lock; never executes a solution/tester."""
from pathlib import Path
import subprocess
root=Path(__file__).resolve().parent
for compiler in ['g++','clang++']:
    for mode in ['plain','bench','profiles']:
        target=root/('build-'+compiler+'-'+mode)
        cmd=[compiler,'-std=c++23','-O2','-Wall','-Wextra']
        if mode!='plain':cmd+=['-DLOCAL_BENCH','-DCLOCK_SCALE=1.1']
        if mode=='profiles':cmd+=['-DCOLFAST_PROFILE=1','-DF3_PROFILE=1','-DAF_PROFILE=1','-DDESIGN_PROFILE=3','-DAS_PROFILE=1','-DPOSET_VERIFY=1','-DSIM_HARNESS']
        cmd+=[str(root/'main.cpp'),'-o',str(target)]
        print(' '.join(cmd),flush=True)
        result=subprocess.run(cmd)
        target.unlink(missing_ok=True)
        if result.returncode:raise SystemExit(result.returncode)
print('All six builds passed.',flush=True)
