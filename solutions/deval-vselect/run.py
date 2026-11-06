"""Call scripts/pahcer_run.py, adding flock to its otherwise-unlocked compiler.

The runner's normal evaluation lock and all recording are left intact.
"""
from pathlib import Path
import importlib.util
import sys
import os

root=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('deval_pahcer_run',root/'scripts/pahcer_run.py')
mod=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=mod
spec.loader.exec_module(mod)
if os.environ.get('DEVAL_GUARD_TEST'):
    mod.COMPILE_CMD+=['-ULOCAL_BENCH','-DDEVAL_REQUEST_LIMIT=0.0']
if os.environ.get('DEVAL_GUARD_STRESS'):
    scale=1.1*float(os.environ['DEVAL_GUARD_STRESS'])
    mod.COMPILE_CMD=[x for x in mod.COMPILE_CMD if not x.startswith('-DCLOCK_SCALE=')]
    mod.COMPILE_CMD+=['-ULOCAL_BENCH',f'-DCLOCK_SCALE={scale:.12g}']
compiler_version=mod.compiler_version
mod.compiler_version=lambda _:compiler_version('g++')
mod.COMPILE_CMD=['flock','-x','/home/sato/ahc074/runs/.lock']+mod.COMPILE_CMD
raise SystemExit(mod.main())
