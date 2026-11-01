"""Column structure of a cmp-* design: column sizes and handle holes per column.
usage: colstat.py RUN SEED"""
import sys
sys.path.insert(0, __file__.rsplit("/solutions/", 1)[0] + "/scripts")
import replay
run, seed = sys.argv[1], int(sys.argv[2])
inp = replay.load_input(seed)
out = replay.parse_output(inp, (replay.resolve_run(run) / "out" / f"{seed:04d}.txt").read_text())
d = out.designs
N = 64
gen = 0
for k in range(6):
    gen |= d[k].opaque
handles = [j for j in range(N) if not (gen >> j) & 1]
print("G", bin(gen).count("1"), "H", len(handles))
cols = {}
for k in range(6, len(d)):
    o = d[k].opaque
    nh = sum((o >> j) & 1 for j in handles)
    ng = bin(o & gen).count("1")
    cols.setdefault(nh, []).append((k, ng))
tot = 0
for c in sorted(cols):
    L = len(cols[c])
    tot += L
    print(f"opaque handles {c:2d}: papers {L:2d}  generic opaque avg {sum(g for _, g in cols[c]) / L:.1f}")
print("papers", tot)
