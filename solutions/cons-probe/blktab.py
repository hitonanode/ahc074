"""Aggregates blkmv_t*_on* / blkcnt_t*_on* over a runm.py output: mean generic moves per request
by (touched blocks t, wanted on)."""
import re, sys
from collections import defaultdict
cnt = defaultdict(float)
mv = defaultdict(float)
for line in open(sys.argv[1]):
    for kv in line.split()[5:]:
        k, _, v = kv.partition("=")
        m = re.match(r"blk(mv|cnt)_t(\d+)_on(\d+)", k)
        if not m:
            continue
        key = (int(m.group(2)), int(m.group(3)))
        if m.group(1) == "cnt":
            cnt[key] += float(v)
# second pass: moves weighted by count
for line in open(sys.argv[1]):
    vals = dict(kv.partition("=")[::2] for kv in line.split()[5:])
    for k, v in vals.items():
        m = re.match(r"blkmv_t(\d+)_on(\d+)", k)
        if m:
            key = (int(m.group(1)), int(m.group(2)))
            c = float(vals.get(f"blkcnt_t{key[0]}_on{key[1]}", 0))
            mv[key] += float(v) * c
tot = sum(cnt.values())
for t in range(12):
    row = []
    for on in range(t + 1):
        if cnt[(t, on)]:
            row.append(f"on{on}:{mv[(t,on)]/cnt[(t,on)]:.2f}({cnt[(t,on)]/tot*100:.1f}%)")
    if row:
        print(f"t={t}: " + " ".join(row))
print("mean", sum(mv.values()) / tot)
