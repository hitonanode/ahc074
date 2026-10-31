"""Classifies the INS lines of a par.py output directory by the kind of the inserted move.

usage: cls.py <dir> [class ...]   (the classes listed get their largest examples printed)
Kinds: paper class before -> after (top = the lifted paper, filler-, col = in place, base, flip),
"(=base op)" when the inserted move is the next move of the plan itself (the gain then comes from
running the plan search again on the rebuilt state), i0 / i>0 = before the plan / inside it.
Columns: count, plan-cost gain (per analysed request), moves saved, fillers left out saved."""
import glob, os, re, sys
from collections import defaultdict

d = sys.argv[1]
agg = defaultdict(lambda: [0, 0.0, 0, 0])
nreq = 0
ex = defaultdict(list)
for f in glob.glob(f"{d}/*.err"):
    s = int(os.path.basename(f).split(".")[0])
    for line in open(f):
        m = re.match(r"^ins_req = (\d+)", line)
        if m:
            nreq += int(m.group(1))
        if not line.startswith("INS "):
            continue
        t = line.split()
        gain = float(t[t.index("gain") + 1])
        mv = t[t.index("moves") + 1].split(">")
        fl = t[t.index("fill") + 1].split(">")
        dm = int(mv[0]) - int(mv[1])
        df = int(fl[0]) - int(fl[1])
        desc = line.split("|", 1)[1].strip()
        if desc.startswith("restart"):
            k = "restart"
        else:
            dt = desc.split()
            i = int(dt[1])
            frm, to = dt[4], dt[6]
            nb = dt[dt.index("next_base_op") + 1]
            pos = dt[dt.index("pos") + 1]
            norm = lambda x: re.sub(r"\d+", "", x)
            same = nb.split(">")[0] == dt[3] and nb.split(">")[1] == pos.split(">")[1]
            k = f"{norm(frm)}->{norm(to)}" + (" (=base op)" if same else "") + (" i0" if i == 0 else " i>0")
        a = agg[k]
        a[0] += 1
        a[1] += gain
        a[2] += dm
        a[3] += df
        ex[k].append((gain, s, line.strip()))
print("requests", nreq)
for k, (n, g, dm, df) in sorted(agg.items(), key=lambda x: -x[1][1]):
    print(f"{k:40s} n {n:4d} gain {g:7.2f} ({g / nreq:.4f}/req)  dmoves {dm:4d} dfill {df:4d}")
if len(sys.argv) > 2:
    for k in sys.argv[2:]:
        for g, s, l in sorted(ex[k], reverse=True)[:8]:
            print(f"{g:.3f} s{s} {l[:250]}")
