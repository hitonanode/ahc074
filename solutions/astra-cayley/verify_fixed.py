#!/usr/bin/env python3
"""Check full solver output equality; this script does not compute contest scores.

All search counts are positive constants and CLOCK_SCALE=0 disables every
wall-clock-dependent cutoff. Thus equality concerns the algorithm, independently
of the intended speed improvement. Score comparisons use pahcer_run separately.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

here = Path(__file__).resolve().parent
root = here.parent.parent
parser = argparse.ArgumentParser()
parser.add_argument('--start', type=int, default=0)
parser.add_argument('--count', type=int, default=16)
parser.add_argument('--output', type=Path, default=here / 'fixed-validation.json')
args = parser.parse_args()
env = dict(os.environ)
env.update(MAP_ITERS='25000', GOPT_STEPS='5000', ANNEAL_ITERS='1000000', CLIMB_ITERS='5000')
sources = [root / 'solutions/astra-search4/main.cpp', here / 'main.cpp']
records = []
with tempfile.TemporaryDirectory(prefix='fixed-', dir=here) as tmp:
    binaries = [Path(tmp) / f'solver{i}' for i in range(2)]
    for source, binary in zip(sources, binaries):
        subprocess.run(['g++', '-std=c++23', '-O2', '-DCLOCK_SCALE=0', str(source), '-o', str(binary)], check=True)
    for seed in range(args.start, args.start + args.count):
        case = root / 'tools/in' / f'{seed:04d}.txt'
        data = case.read_bytes()
        outputs = [subprocess.run([str(binary)], input=data, capture_output=True, env=env, check=True, timeout=60)
                   for binary in binaries]
        same = outputs[0].stdout == outputs[1].stdout
        records.append({'seed': seed, 'equal': same, 'bytes': [len(x.stdout) for x in outputs],
                        'sha256': [hashlib.sha256(x.stdout).hexdigest() for x in outputs]})
        if not same:
            raise RuntimeError(f'full stdout differs at seed {seed}')
result = {'purpose': 'algorithmic equality, not contest score evaluation', 'clock_scale': 0,
          'fixed_work': {k: env[k] for k in ['MAP_ITERS', 'GOPT_STEPS', 'ANNEAL_ITERS', 'CLIMB_ITERS']},
          'source_sha256': [hashlib.sha256(p.read_bytes()).hexdigest() for p in sources],
          'cases': len(records), 'mismatches': 0, 'records': records}
args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({'cases': len(records), 'full_stdout_mismatches': 0}))
