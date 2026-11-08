"""Standard pahcer runner with per-arm compilers and flags (solutions/jflags-notes; modelled on
solutions/dcomp-notes/task10_run.py). Only prepare/compile change: builds run under the evaluation lock
with nice, and each arm of a --compare (in the order given) gets its own compile command.

JFLAGS_ARMS is a JSON list with one entry per arm: [compiler, "flags"], e.g.
  [["clang++", "-std=gnu++23 -O2 -march=native"], ["clang++", "-std=gnu++23 -O2 -march=native -ftrivial-auto-var-init=zero"]]
The flags replace the standard "-std=c++23 -O2"; -DCLOCK_SCALE=1.1 -DLOCAL_BENCH are always added (as in
the standard runner). The same solution may be given several times (run ids get -2, -3, ...). The arm's
flags are saved in meta.json (jflags). No evaluation, timing, lock, recording or solver policy is replaced.
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
spec = importlib.util.spec_from_file_location('jflags_pahcer', root / 'scripts/pahcer_run.py')
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)
arms = json.loads(os.environ.get('JFLAGS_ARMS', '[]'))
# JFLAGS_HELD=1: the caller already holds the evaluation lock for the whole compile phase (one lock wait
# instead of one per build); the builds then only run under nice.
prefix = (['nice', '-n', '10'] if os.environ.get('JFLAGS_HELD') == '1'
          else ['flock', '-x', '/home/sato/ahc074/runs/.lock', 'nice', '-n', '10'])
original_prepare = mod.prepare_run
count = [0]


def prepare(solution, *args, **kwargs):
    i = count[0]
    count[0] += 1
    compiler, flags = arms[i] if i < len(arms) else ('g++', '-std=c++23 -O2')
    mod.COMPILE_CMD = prefix + [compiler] + shlex.split(flags) + ['-DCLOCK_SCALE=1.1', '-DLOCAL_BENCH']
    arm = original_prepare(solution, *args, **kwargs)
    arm['meta']['compiler'] = mod.compiler_version(compiler)
    arm['meta']['jflags'] = {'compiler': compiler, 'flags': flags}
    mod.save_meta(arm['run_dir'], arm['meta'])
    return arm


mod.prepare_run = prepare
raise SystemExit(mod.main())
