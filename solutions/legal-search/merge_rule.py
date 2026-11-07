"""A cheap rule for the stage 1 savings, checked offline: for every order where the SOTA moves a paper x twice
(moves i < j), drop move j and send x at move i directly to its place in the end order T: just above the
first paper after x in T that the remaining sequence does not move after move i (the bottom if none). The
other moves keep their anchors (each paper is inserted just above the same paper as in the SOTA's sequence,
or at the same depth if it went to the bottom). Accepted if every move is legal and the end order is T.

Usage: python merge_rule.py RUN A B [STAGE1_DIR]
Prints the number of orders with a double move, the rule's successes, and the overlap with the search.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import replay  # noqa: E402


def visible(papers, order, k):
    cov = 0
    for x in order:
        if x == k:
            return bool(papers[k].opaque & ~cov)
        cov |= papers[x].opaque
    return False


def anchors_of(start, ops):
    """For each move, the paper just below the moved paper right after the move (None: the bottom)."""
    order = list(start)
    res = []
    for k, d in ops:
        order.remove(k)
        order.insert(d, k)
        res.append(order[d + 1] if d + 1 < len(order) else None)
    return res, order


def try_rule(papers, start, ops, end_t):
    from collections import Counter
    cnt = Counter(k for k, _ in ops)
    anchors, _ = anchors_of(start, ops)
    tpos = {x: i for i, x in enumerate(end_t)}
    for x, c in cnt.items():
        if c != 2:
            continue
        i, j = [t for t, (k, _) in enumerate(ops) if k == x]
        new = [(k, anchors[t]) for t, (k, _) in enumerate(ops) if t != j]
        later = {k for t, (k, _) in enumerate(ops) if t > i and t != j}
        # the first paper after x in T that does not move after move i
        q = None
        for y in end_t[tpos[x] + 1:]:
            if y not in later:
                q = y
                break
        new[i] = (x, q)
        order = list(start)
        ok = True
        out = []
        for k, a in new:
            if not visible(papers, order, k):
                ok = False
                break
            order.remove(k)
            d = order.index(a) if a is not None else len(order)
            order.insert(d, k)
            out.append((k, d))
        if ok and order == end_t:
            return out
    return None


def main():
    run = replay.resolve_run(sys.argv[1])
    a, b = int(sys.argv[2]), int(sys.argv[3])
    stage1 = Path(sys.argv[4]) if len(sys.argv) > 4 else None
    doubles = hits = search_imp = both = 0
    for seed in range(a, b):
        inp = replay.load_input(seed)
        out = replay.parse_output(inp, replay.out_path(run, seed).read_text())
        imp = set()
        if stage1 and (stage1 / f"{seed:04d}.txt").exists():
            for line in (stage1 / f"{seed:04d}.txt").read_text().splitlines():
                t = line.split()
                if t[5] == "imp":
                    imp.add(int(t[1]))
        search_imp += len(imp)
        game = replay.Game(inp, out.designs)
        for r, ops in enumerate(out.queries):
            start = list(game.order)
            for k, d in ops:
                game.move(k, d)
            game.finish(r)
            if len({k for k, _ in ops}) == len(ops):
                continue
            doubles += 1
            res = try_rule(out.designs, start, ops, list(game.order))
            if res is not None:
                hits += 1
                both += r in imp
                # independent check of the rewritten sequence
                g = replay.Game(inp, out.designs)
                g.order = list(start)
                for k, d in res:
                    g.move(k, d)
                assert g.order == list(game.order)
    print(f"seeds {a}-{b - 1}: orders with a double move {doubles}, rule hits {hits}, search improvements {search_imp}, "
          f"rule hits that the search also found {both}")


if __name__ == "__main__":
    main()
