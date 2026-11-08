"""Standard pahcer runner with per-arm compilers and flags (solutions/jflags-notes; modelled on
solutions/dcomp-notes/task10_run.py). Only prepare/compile change: builds run under the evaluation lock
with nice, and each arm of a --compare (in the order given) gets its own compile command.

JFLAGS_ARMS is a JSON list with one entry per arm: [compiler, "flags"], e.g.
  [["clang++", "-std=gnu++23 -O2 -march=native"], ["clang++", "-std=gnu++23 -O2 -march=native -ftrivial-auto-var-init=zero"]]
The flags are used exactly as supplied: production builds do not add LOCAL_BENCH or CLOCK_SCALE. The same solution may be given several times (run ids get -2, -3, ...). The arm's
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
# Optional crafted inputs: keep official execution, locking and replay; change only the input source.
custom_inputs = Path(os.environ['REVIEW_INPUT_DIR']).resolve() if os.environ.get('REVIEW_INPUT_DIR') else None
if custom_inputs:
    original_write_config = mod.write_config
    def write_config(*args, **kwargs):
        kwargs['in_dir'] = custom_inputs
        return original_write_config(*args, **kwargs)
    mod.write_config = write_config
    original_order_input = mod.order_input
    def order_input(root, in_dir, seed, j):
        return original_order_input(root, custom_inputs, seed, j)
    mod.order_input = order_input
    def load_input(seed):
        return mod.replay.parse_input((custom_inputs / f'{seed:04d}.txt').read_text())
    mod.replay.load_input = load_input
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
    mod.COMPILE_CMD = prefix + [compiler] + shlex.split(flags)
    arm = original_prepare(solution, *args, **kwargs)
    arm['meta']['compiler'] = mod.compiler_version(compiler)
    arm['meta']['jflags'] = {'compiler': compiler, 'flags': flags}
    if custom_inputs: arm['meta']['review_input_dir'] = str(custom_inputs)
    mod.save_meta(arm['run_dir'], arm['meta'])
    return arm


mod.prepare_run = prepare
raise SystemExit(mod.main())
