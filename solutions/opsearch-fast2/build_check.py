"""Compile both preprocessor paths serially under the shared lock; execute neither binary."""
import fcntl
import json
from pathlib import Path
import subprocess

folder = Path(__file__).resolve().parent
jobs = [('clang-bench', ['clang++', '-std=c++23', '-O2', '-DLOCAL_BENCH']),
        ('gcc-release', ['g++', '-std=c++23', '-O2'])]
results = []
print('Waiting for the evaluation lock before compilation.', flush=True)
with Path('/home/sato/ahc074/runs/.lock').open('rb') as lock:
    fcntl.flock(lock, fcntl.LOCK_EX)
    for label, options in jobs:
        binary = folder / ('.build-' + label)
        command = [*options, str(folder / 'main.cpp'), '-o', str(binary)]
        result = subprocess.run(command, capture_output=True, text=True)
        (folder / (label + '.log')).write_text(result.stdout + result.stderr)
        results.append({'label': label, 'command': command, 'returncode': result.returncode})
        binary.unlink(missing_ok=True)
        print(label, result.returncode, flush=True)
        assert result.returncode == 0, result.stderr
(folder / 'build-check.json').write_text(json.dumps(results, indent=2) + '\n')
