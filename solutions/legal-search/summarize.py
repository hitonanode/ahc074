"""Summary of the stage 1 results (same_end outputs) with the SOTA's move labels.

Usage: python summarize.py RUN RESULT_DIR [EXAMPLES]
"""
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import replay  # noqa: E402


def main():
    run = replay.resolve_run(sys.argv[1])
    res_dir = Path(sys.argv[2])
    n_examples = int(sys.argv[3]) if len(sys.argv) > 3 else 0
    status = Counter()
    by_gap = defaultdict(Counter)
    saved = 0
    orders = 0
    seeds = 0
    imp_rows = []
    dbl_status = Counter()
    for path in sorted(res_dir.glob("*.txt")):
        lines = [l for l in path.read_text().splitlines() if l.strip()]
        if len(lines) != 1024:
            print(f"skip {path.name}: {len(lines)} lines")
            continue
        seeds += 1
        seed = int(path.stem)
        inp = replay.load_input(seed)
        out = replay.parse_output(inp, replay.out_path(run, seed).read_text())
        ann = replay.parse_annotations(replay.err_path(run, seed).read_text(errors="replace"), inp.k)
        for line in lines:
            tok = line.split("|")[0].split()
            r, m, lb, best, st = int(tok[1]), int(tok[2]), int(tok[3]), int(tok[4]), tok[5]
            orders += 1
            status[st] += 1
            by_gap[min(m - lb, 9)][st] += 1
            ops = out.queries[r]
            cnt = Counter(k for k, _ in ops)
            dbl = any(v > 1 for v in cnt.values())
            if dbl:
                dbl_status[st] += 1
            if st == "imp":
                saved += m - best
                labels = ann.labels_of(r, m)
                new_ops = [tuple(map(int, t.split(":"))) for t in tok[7:]]
                imp_rows.append((seed, r, m, lb, best, labels, ops, new_ops, dbl))
    print(f"seeds {seeds}, orders {orders}")
    for st, c in status.most_common():
        print(f"  {st}: {c} ({100 * c / orders:.3f}%)")
    print(f"improved orders: {status['imp']} ({100 * status['imp'] / orders:.4f}%), moves saved {saved}, "
          f"mean saving per order {saved / orders:.5f}")
    print("orders where the SOTA moved a paper twice:", dict(dbl_status))
    g1 = by_gap[1]
    full = status["opt0"] + g1["opt1"] + g1["opt1m"]
    print(f"proven optimal over all legal sequences (m = LB, or m - LB = 1 and no single-move solution): {full} "
          f"({100 * full / orders:.2f}%)")
    single_only = status["opt1"] - g1["opt1"]
    print(f"proven only in the single-move class (m - LB >= 2): {single_only} ({100 * single_only / orders:.2f}%)")
    print(f"  plus opt1m with m - LB >= 2: {status['opt1m'] - g1['opt1m']}")
    print("by m - LB (9 = 9 or more):")
    for g in sorted(by_gap):
        row = by_gap[g]
        tot = sum(row.values())
        print(f"  gap {g}: {tot} orders, " + ", ".join(f"{k} {v}" for k, v in sorted(row.items())))
    # what the improvements remove: papers moved twice by the SOTA that move once
    kinds = Counter()
    for seed, r, m, lb, best, labels, ops, new_ops, dbl in imp_rows:
        old = Counter(k for k, _ in ops)
        new = Counter(k for k, _ in new_ops)
        removed = []
        for i, (k, _) in enumerate(ops):
            pass
        diff_labels = []
        for k in old:
            if new[k] < old[k]:
                # labels of the moves of paper k in the SOTA
                diff_labels.append("+".join(labels[i] for i, (kk, _) in enumerate(ops) if kk == k) + f"->{new[k]}")
        kinds[" ".join(sorted(diff_labels))] += 1
    print("papers whose moves were reduced (SOTA labels of that paper -> moves in the new sequence):")
    for k, v in kinds.most_common(20):
        print(f"  {v:4d}  {k}")
    for row in imp_rows[:n_examples]:
        seed, r, m, lb, best, labels, ops, new_ops, dbl = row
        print(f"example seed {seed} r {r}: m {m} LB {lb} -> {best}")
        print("   SOTA:", " ".join(f"{k}>{d}:{l}" for (k, d), l in zip(ops, labels)))
        print("   new :", " ".join(f"{k}>{d}" for k, d in new_ops))


if __name__ == "__main__":
    main()
