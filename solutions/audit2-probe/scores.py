"""Writes `seed score` lines from the err files of a run1.py output directory. usage: scores.py <dir> > file"""
import re, sys
from pathlib import Path
for f in sorted((Path(sys.argv[1]) / "err").glob("*.txt")):
    m = re.findall(r"^Score = (\d+)", f.read_text(), re.M)
    print(int(f.stem), m[-1] if m else 0)
