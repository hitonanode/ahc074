"""Stage 1 statistics of the SOTA outputs: for every order, the start order S, the end order T, the number
of moves m, the visibility-free lower bound LB = K - LCS(S, T), and the number of papers moved twice.

Usage: python endpoints.py RUN SEED_FROM SEED_TO OUT.tsv
Writes one line per order: seed r m LB moved_distinct double labels
"""
import bisect
import sys
from multiprocessing import Pool
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import replay  # noqa: E402


def lcs_perm(a, b):
    """LCS of two permutations of the same set = LIS of the positions in b of the items of a."""
    pos = {x: i for i, x in enumerate(b)}
    tails = []
    for x in a:
        v = pos[x]
        i = bisect.bisect_left(tails, v)
        if i == len(tails):
            tails.append(v)
        else:
            tails[i] = v
    return len(tails)


def job(args):
    run, seed = args
    run_dir = replay.resolve_run(run)
    inp = replay.load_input(seed)
    out = replay.parse_output(inp, replay.out_path(run_dir, seed).read_text())
    ann = replay.parse_annotations(replay.err_path(run_dir, seed).read_text(errors="replace"), inp.k)
    game = replay.Game(inp, out.designs)
    rows = []
    for r, ops in enumerate(out.queries):
        s = list(game.order)
        for k, d in ops:
            game.move(k, d)
        assert game.finish(r)
        t = game.order
        m = len(ops)
        lb = inp.k - lcs_perm(s, t)
        cnt = {}
        for k, _ in ops:
            cnt[k] = cnt.get(k, 0) + 1
        dbl = sum(1 for v in cnt.values() if v > 1)
        labels = ann.labels_of(r, m)
        rows.append(f"{seed}\t{r}\t{m}\t{lb}\t{len(cnt)}\t{dbl}\t{','.join(labels) if labels else '-'}")
    return rows


def main():
    run, a, b, out = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
    with Pool(8) as pool:
        res = pool.map(job, [(run, s) for s in range(a, b)])
    with open(out, "w") as f:
        f.write("seed\tr\tm\tLB\tmoved\tdouble\tlabels\n")
        for rows in res:
            f.write("\n".join(rows) + "\n")


if __name__ == "__main__":
    main()
