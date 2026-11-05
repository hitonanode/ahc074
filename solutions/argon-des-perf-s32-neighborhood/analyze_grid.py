"""Read completed runs, sequentially, while holding the evaluation lock."""
from pathlib import Path
import subprocess
import sys

here = Path(__file__).resolve().parent
base = '20261106-045540_argon-des-design-packed'

def run(script, args, output):
    with (here / output).open('w') as f:
        subprocess.run([sys.executable, str(here/script), *args], stdout=f, stderr=subprocess.STDOUT, check=True)
    print(output, flush=True)

run('summarize.py', [base, '20261106-050229_argon-des-perf-s32w75',
                    '20261106-050229_argon-des-perf-s32w80', '--output', 'grid2000.json'], 'grid-summary2000.log')
for weight in [65, 75, 80]:
    candidate = f'20261106-050229_argon-des-perf-s32w{weight}'
    run('model_effect.py', [base, candidate, '--weight', str(weight/100), '--end', '500',
                           '--output', f'model-w{weight}-500.json'], f'model-w{weight}-500.log')
    if weight != 80:  # Already requested separately, without duplicating the replay.
        run('effects.py', [base, candidate, '--general', '--end', '500',
                          '--output', f'effects-w{weight}-500.json'], f'effects-w{weight}-500.log')
