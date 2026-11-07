"""Aggregates the `#roll` / `#rollval` lines of legal-roll runs (all order lists of a --design-from run).

Usage: python roll_stats.py RUN [RUN ...]
"""
import math
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import replay  # noqa: E402


def err_files(run_dir: Path):
    yield from sorted((run_dir / "err").glob("*.txt"))
    orders = run_dir / "orders"
    if orders.is_dir():
        for j in sorted(orders.iterdir()):
            yield from sorted((j / "err").glob("*.txt"))


def main():
    for arg in sys.argv[1:]:
        run = replay.resolve_run(arg)
        dec = changed = 0
        by_src = Counter()
        ncand = Counter()
        pred = []
        val = []
        val_by_src = {}
        files = 0
        for path in err_files(run):
            files += 1
            for line in path.read_text(errors="replace").splitlines():
                if line.startswith("#roll "):
                    tok = line.split()
                    ne, nt, ch = int(tok[3]), int(tok[4]), int(tok[5])
                    cands = [t.split(":") for t in tok[6:]]
                    dec += 1
                    ncand[nt] += 1
                    if ch:
                        changed += 1
                        src = int(cands[ch][0])
                        by_src[src] += 1
                        pred.append(float(cands[0][3]) - float(cands[ch][3]))
                elif line.startswith("#rollval "):
                    tok = line.split()
                    src, v0, vc = int(tok[2]), float(tok[3]), float(tok[4])
                    val.append(v0 - vc)
                    val_by_src.setdefault(src, []).append(v0 - vc)
        print(f"{run.name}: files {files}, decisions {dec}, changed {changed} ({100 * changed / max(dec, 1):.1f}%)")
        print("  candidates per decision:", dict(sorted(ncand.items())))
        print("  chosen source (1 pooled, 2 slot variant, 3 deletion):", dict(sorted(by_src.items())))
        if pred:
            print(f"  predicted gain per changed decision {sum(pred) / len(pred):.4f}")
        if val:
            m = sum(val) / len(val)
            sd = math.sqrt(sum((x - m) ** 2 for x in val) / max(len(val) - 1, 1))
            print(f"  validated gain per changed decision {m:.4f} +- {sd / math.sqrt(len(val)):.4f} (n {len(val)})")
            for src, xs in sorted(val_by_src.items()):
                mm = sum(xs) / len(xs)
                s2 = math.sqrt(sum((x - mm) ** 2 for x in xs) / max(len(xs) - 1, 1))
                print(f"    source {src}: {mm:.4f} +- {s2 / math.sqrt(len(xs)):.4f} (n {len(xs)})")
            print(f"  validated gain per decision {sum(val) / dec:.5f} moves")


if __name__ == "__main__":
    main()
