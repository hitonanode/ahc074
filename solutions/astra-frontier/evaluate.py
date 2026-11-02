#!/usr/bin/env python3
"""Call the unchanged pahcer_run.py with a bounded CPU count (default 4)."""
import os
import pathlib
import runpy
import sys

root = pathlib.Path(__file__).resolve().parents[2]
workers = int(os.environ.get('FRONTIER_WORKERS', '4'))
assert 1 <= workers <= len(os.sched_getaffinity(0))
os.cpu_count = lambda: workers
script = root / 'scripts/pahcer_run.py'
sys.argv[0] = str(script)
runpy.run_path(str(script), run_name='__main__')
