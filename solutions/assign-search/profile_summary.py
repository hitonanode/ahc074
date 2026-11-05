#!/usr/bin/env python3
"""保存済み #assign 行の集計。解法やテスターは実行しない。"""
from pathlib import Path
from collections import defaultdict
import sys
run = sys.argv[1] if len(sys.argv) > 1 else '20261105-101115_assign-search'
files = list((Path('/home/sato/ahc074/runs') / run / 'err').glob('*.txt'))
rows = defaultdict(lambda: [0.0] * 12)
for f in files:
    for line in f.read_text().splitlines():
        if not line.startswith('#assign '): continue
        t = line.split()
        if int(t[1]) == 0: continue
        for i, v in enumerate(t[3:]): rows[t[2]][i] += float(v) / len(files)
print('run:', run, 'seeds:', len(files), 'phases: 1-4')
print('operator proposed candidates accepted improvements best_gain entering new_valid propose_Mcycles matching_Mcycles')
for name, r in rows.items():
    print(name, *(f'{r[i]:.4f}' for i in [0,1,3,5,7,8,9,10,11]))
