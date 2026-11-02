"""Replay a prepared output through the official tester for rule validation only.
This is NOT a solver and is not used to measure online-policy quality.
"""
import sys
from pathlib import Path
lines=iter(Path(sys.argv[1]).read_text().splitlines())
n,k,p,r=map(int,sys.stdin.readline().split())
for _ in range(p):sys.stdin.readline()
for _ in range(k):print(next(lines))
sys.stdout.flush()
for _ in range(r):
    request=sys.stdin.readline().strip()
    if not request or request=='-1':sys.exit()
    m=int(next(lines));print(m)
    for _ in range(m):print(next(lines))
    sys.stdout.flush()
