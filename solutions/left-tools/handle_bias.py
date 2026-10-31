"""Per-handle color bias of a hub-type design (left-tools).

For each seed of a run: finds the generic windows (union of the small flip papers), orders the
handle windows by depth (number of papers with a hole there), and for each handle h_m reports the
number of targets whose paper has a hole at h_m and the majority fraction p_m among them, next to
the global black count of the window over all 256 targets. Used to see whether the deep handles,
shared by almost every target, could be put on more unbalanced windows.

usage: python3 handle_bias.py RUN [SEEDS]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import replay  # noqa: E402


def analyze(run_dir: Path, seed: int):
    inp = replay.load_input(seed)
    out = replay.parse_output(inp, replay.out_path(run_dir, seed).read_text())
    pap = out.designs
    n = inp.n
    flips = [p for p in pap if 0 < bin(p.opaque).count("1") <= 8]
    gmask = 0
    for p in flips:
        gmask |= p.opaque
    holes = [sum(1 for p in pap if not (p.opaque >> w & 1)) for w in range(n)]
    handles = sorted([w for w in range(n) if not (gmask >> w & 1)], key=lambda w: holes[w])
    # targets -> paper (dedicated: opaque on G except pair differences, matches A_u where opaque)
    tpaper = {}
    for u, a in enumerate(inp.target):
        for k, p in enumerate(pap):
            if p.opaque & ~gmask == 0:  # generic paper (base or flip)
                continue
            if (a ^ p.black) & p.opaque == 0:
                tpaper[u] = k
                break
    rows = []
    for m, w in enumerate(handles):
        tg = [u for u in range(inp.p) if u in tpaper and not (pap[tpaper[u]].opaque >> w & 1)]
        nb = sum(inp.target[u] >> w & 1 for u in tg)
        p = nb / len(tg) if tg else 0.5
        glob = sum(a >> w & 1 for a in inp.target)
        rows.append((m, w, len(tg), max(p, 1 - p), glob))
    gwin = [sum(a >> w & 1 for a in inp.target) for w in range(n) if gmask >> w & 1]
    return rows, gwin


def main():
    run = replay.resolve_run(sys.argv[1])
    seeds = range(int(sys.argv[2])) if len(sys.argv) > 2 else range(20)
    agg = {}
    tot_cost = 0.0
    tot_cost_unb = 0.0
    for s in seeds:
        rows, gwin = analyze(run, s)
        H = len(rows)
        for m, w, nt, pm, glob in rows:
            d = H - 1 - m  # 0 = deepest
            a = agg.setdefault(d, [0, 0.0, 0.0, 0])
            a[0] += nt
            a[1] += pm * nt
            a[2] += abs(glob - 128)
            a[3] += 1
            tot_cost += nt * 2 * pm * (1 - pm)
            tot_cost_unb += nt * 0.5
        devs = sorted((abs(g - 128) for g in gwin), reverse=True)
        print(f"seed {s}: H={H}, G={len(gwin)}, top G |dev| {devs[:5]}, deepest handles |dev| "
              f"{[abs(r[4] - 128) for r in rows[::-1][:5]]}")
    print("depth (0 = deepest): mean #targets with a hole, majority p, mean |global count - 128|")
    for d in sorted(agg):
        nt, pp, dev, c = agg[d]
        print(f"  {d:2d}: {nt / c:6.1f}  {pp / max(nt, 1):.3f}  {dev / c:5.1f}")
    print(f"sum n 2p(1-p) / sum n 0.5 = {tot_cost / tot_cost_unb:.4f}")


if __name__ == "__main__":
    main()
