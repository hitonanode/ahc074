"""Independent check of the stage-2b sequences (same_end mode 8, `dimp` lines) with scripts/replay.py: every
move is of a visible paper (from the order before the request), the display is the request, and the sequence
is shorter than the SOTA's. The end order is free (it is reported as different / same as the SOTA's).

Usage: python verify_display.py RUN RESULT_FILE...
"""
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import replay  # noqa: E402


def main():
    run = replay.resolve_run(sys.argv[1])
    want = defaultdict(dict)
    for path in sys.argv[2:]:
        for line in Path(path).read_text().splitlines():
            t = line.split()
            if len(t) > 5 and t[5] == "dimp":
                ops = [tuple(map(int, x.split(":"))) for x in t[11:] if ":" in x]
                want[int(t[0])][int(t[1])] = (int(t[2]), ops)
    ok = bad = 0
    for seed in sorted(want):
        inp = replay.load_input(seed)
        out = replay.parse_output(inp, replay.out_path(run, seed).read_text())
        game = replay.Game(inp, out.designs)
        for r, ops in enumerate(out.queries):
            if r in want[seed]:
                m, new = want[seed][r]
                start = list(game.order)
                ref = replay.Game(inp, out.designs)
                ref.order = list(start)
                for k, d in ops:
                    ref.move(k, d)
                test = replay.Game(inp, out.designs)
                test.order = list(start)
                verdict = "ok"
                try:
                    for k, d in new:
                        test.move(k, d)
                except replay.InvalidMove as e:
                    verdict = f"invalid ({e})"
                if verdict == "ok" and test.display() != inp.target[inp.requests[r]]:
                    verdict = "wrong display"
                if verdict == "ok" and not len(new) < m:
                    verdict = "not shorter"
                same = test.order == ref.order
                print(f"{seed} {r} m={m} new={len(new)} {verdict} end_order={'same' if same else 'different'}")
                ok += verdict == "ok"
                bad += verdict != "ok"
            if r == max(want[seed]):
                break
            for k, d in ops:
                game.move(k, d)
            game.finish(r)
    print(f"verified {ok} ok, {bad} failed")


if __name__ == "__main__":
    main()
