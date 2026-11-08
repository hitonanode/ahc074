"""Review harness (solutions/review-fable1): a copy of solutions/jflags-notes/run.py with one change.
When JFLAGS_RAW=1, the flags of each arm are used as given, without the standard -DCLOCK_SCALE=1.1
-DLOCAL_BENCH, so that production builds (no LOCAL_BENCH, CLOCK_SCALE 1.0) can be evaluated.

JFLAGS_ARMS is a JSON list with one entry per arm: [compiler, "flags"].
Builds run under the evaluation lock with nice. Always run with --no-record.
"""
from pathlib import Path
import importlib.util
import json
import os
import shlex
import sys

sys.dont_write_bytecode = True
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
root = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('review_pahcer', root / 'scripts/pahcer_run.py')
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)
arms = json.loads(os.environ.get('JFLAGS_ARMS', '[]'))
raw = os.environ.get('JFLAGS_RAW') == '1'
prefix = (['nice', '-n', '10'] if os.environ.get('JFLAGS_HELD') == '1'
          else ['flock', '-x', '/home/sato/ahc074/runs/.lock', 'nice', '-n', '10'])
original_prepare = mod.prepare_run
count = [0]


def prepare(solution, *args, **kwargs):
    i = count[0]
    count[0] += 1
    compiler, flags = arms[i] if i < len(arms) else ('g++', '-std=c++23 -O2')
    extra = [] if raw else ['-DCLOCK_SCALE=1.1', '-DLOCAL_BENCH']
    mod.COMPILE_CMD = prefix + [compiler] + shlex.split(flags) + extra
    arm = original_prepare(solution, *args, **kwargs)
    arm['meta']['compiler'] = mod.compiler_version(compiler)
    arm['meta']['jflags'] = {'compiler': compiler, 'flags': flags, 'raw': raw}
    mod.save_meta(arm['run_dir'], arm['meta'])
    return arm


mod.prepare_run = prepare
raise SystemExit(mod.main())
