"""Summarize the final compare after acquiring the evaluation lock through whenidle.sh."""
import subprocess
import sys
from pathlib import Path

here = Path(__file__).resolve().parent
commands = [
    ([sys.executable, str(here / 'summarize.py'),
      '20261106-015207_argon-des-perf-condbound', '20261106-015850_argon-des-perf-gaincache',
      '--output', 'gaincache-2000.json'], here / 'gaincache-summary-2000.log'),
    ([sys.executable, str(here.parent / 'argon-des-perf-gaincache/final_audit.py'),
      '20261106-015850_argon-des-perf-gaincache'], here.parent / 'argon-des-perf-gaincache/final-audit.log'),
    ([sys.executable, str(here / 'measurement_table.py')], here / 'measurement-table.log'),
]
for command, log in commands:
    with log.open('w') as out:
        subprocess.run(command, stdout=out, stderr=subprocess.STDOUT, check=True)
    print(log.name, 'done', flush=True)
