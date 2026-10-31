"""Runs one binary under several env settings (via run1.py) and compares each to the first.
usage: sweep.py <binary> <outdir> <first seed> <end seed> <common ENV=VAL,...> <name:ENV=VAL,...> ...
(an empty common/config part is written as '-')"""
import subprocess, sys
from pathlib import Path
here = Path(__file__).resolve().parent
binary, outdir, lo, hi, common = sys.argv[1:6]
configs = sys.argv[6:]
common_env = [] if common == "-" else common.split(",")
files = []
for cfg in configs:
    name, _, envs = cfg.partition(":")
    env = common_env + ([] if envs in ("", "-") else envs.split(","))
    d = Path(outdir) / name
    res = subprocess.run([sys.executable, str(here / "run1.py"), binary, str(d), lo, hi] + env,
                         capture_output=True, text=True).stdout
    f = Path(outdir) / f"{name}.txt"
    f.write_text(res)
    files.append((name, f))
for name, f in files[1:]:
    out = subprocess.run([sys.executable, str(here / "cmp.py"), str(files[0][1]), str(f)], capture_output=True, text=True).stdout
    print(f"{name}: {out.strip()}")
