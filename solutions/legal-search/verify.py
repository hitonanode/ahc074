"""Independent check of the shortened sequences found by same_end (stage 1), with scripts/replay.py.

For every `imp` / `mimp` line of the given result files: replay the SOTA output up to the order (the start
order S), apply the found moves with the visibility check (replay.Game.move raises InvalidMove), and check
that the end order equals the SOTA's end order T and that the display equals the request.

Usage: python verify.py RUN RESULT_FILE...
Prints one line per checked sequence and a summary.
"""
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import replay  # noqa: E402


def parse_found(line):
    """(seed, r, m, [(kind, length, ops)]) of a result line."""
    parts = line.split("|")
    head = parts[0].split()
    seed, r, m = int(head[0]), int(head[1]), int(head[2])
    found = []
    for i, part in enumerate(parts):
        tok = part.split()
        if i == 0:
            tok = tok[4:]
        if len(tok) >= 3 and tok[1] in ("imp", "mimp"):
            ops = [tuple(map(int, t.split(":"))) for t in tok[3:]]
            found.append((tok[1], int(tok[0]), ops))
    return seed, r, m, found


def main():
    run = replay.resolve_run(sys.argv[1])
    wanted = defaultdict(list)
    for path in sys.argv[2:]:
        for line in Path(path).read_text().splitlines():
            if not line.strip() or line.startswith(("TEST", "BOUND", "SEARCH")):
                continue
            seed, r, m, found = parse_found(line)
            for kind, length, ops in found:
                wanted[seed].append((r, m, kind, length, ops))
    ok = bad = 0
    for seed in sorted(wanted):
        inp = replay.load_input(seed)
        out = replay.parse_output(inp, replay.out_path(run, seed).read_text())
        todo = {r: v for r, *v in wanted[seed]}
        game = replay.Game(inp, out.designs)
        for r, ops in enumerate(out.queries):
            if r in todo:
                m, kind, length, new_ops = todo[r]
                start = list(game.order)
                # the SOTA's end order
                ref = replay.Game(inp, out.designs)
                ref.order = list(start)
                for k, d in ops:
                    ref.move(k, d)
                end_t = list(ref.order)
                test = replay.Game(inp, out.designs)
                test.order = list(start)
                verdict = "ok"
                try:
                    for k, d in new_ops:
                        test.move(k, d)
                except replay.InvalidMove as e:
                    verdict = f"invalid ({e})"
                if verdict == "ok" and test.order != end_t:
                    verdict = "different end order"
                if verdict == "ok" and test.display() != inp.target[inp.requests[r]]:
                    verdict = "wrong display"
                if verdict == "ok" and len(new_ops) != length:
                    verdict = f"length {len(new_ops)} != reported {length}"
                if verdict == "ok" and not len(new_ops) < m:
                    verdict = "not shorter"
                print(f"{seed} {r} {kind} m={m} new={len(new_ops)} {verdict}")
                if verdict == "ok":
                    ok += 1
                else:
                    bad += 1
            for k, d in ops:
                game.move(k, d)
            game.finish(r)
    print(f"verified {ok} ok, {bad} failed")


if __name__ == "__main__":
    main()
