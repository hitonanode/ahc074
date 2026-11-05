"""Summarize and diagnose the 32-sample runner-up ablation, sequentially."""
from pathlib import Path
import subprocess
import sys

here = Path(__file__).resolve().parent
base = '20261106-051209_argon-des-design-packed'
suffixes = ['nonhead32', 'nonhead32wide']

def run(script, args, output):
    with (here/output).open('w') as f:
        subprocess.run([sys.executable, str(here/script), *args], stdout=f, stderr=subprocess.STDOUT, check=True)
    print(output, flush=True)

run('summarize.py', [base, *[f'20261106-051209_argon-des-perf-{s}' for s in suffixes],
                    '--output', 'nonhead500.json'], 'nonhead-summary500.log')
for suffix in suffixes:
    candidate = f'20261106-051209_argon-des-perf-{suffix}'
    run('effects.py', [base, candidate, '--end', '500', '--output', f'effects-{suffix}-500.json'],
        f'effects-{suffix}-500.log')
