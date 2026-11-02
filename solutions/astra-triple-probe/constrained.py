#!/usr/bin/env python3
"""Run the constrained structural probe using the small saved design JSON."""
import argparse
import json
from pathlib import Path
import subprocess

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('design', type=Path)
p.add_argument('output', type=Path)
p.add_argument('--candidates', type=int, default=16)
p.add_argument('--steps', type=int, default=10000)
args = p.parse_args()
here = Path(__file__).resolve().parent
design = json.loads(args.design.read_text())
text = '\n'.join(design['patterns'] + design['sheets']) + '\n'
proc = subprocess.run([str(here / 'constrained'), str(args.candidates), str(args.steps)],
                      input=text, capture_output=True, text=True, check=True)
args.output.write_text(proc.stdout)
args.output.with_suffix('.log').write_text(proc.stderr)
print(proc.stderr, end='')
print(proc.stdout, end='')
