"""Explain selected saved witnesses by replaying deletions and inspecting the final owners."""
from pathlib import Path
import fcntl
import json
import sys

sys.dont_write_bytecode = True
from analyze import align, anchors, replay


def details(example, run):
    seed, r = example["seed"], example["r"]
    inp = replay.load_input(seed)
    out = replay.parse_output(inp, replay.out_path(run, seed).read_text())
    before, after, start = example["before"], example["after"], example["start_order"]
    bs = anchors(start, before)
    matched = {i for i, j in align(before, after)}
    removed = [i for i in range(len(before)) if i not in matched]

    def deletion(skip):
        g = replay.Game(inp, out.designs)
        g.order = start.copy()
        for i, (k, depth, label) in enumerate(before):
            if i in skip: continue
            p = g.order.index(k)
            anchor = bs[i]
            d = 0 if anchor < 0 else g.order.index(anchor) + 1
            if p < d: d -= 1
            if p == d: continue
            try:
                g.move(k, d)
            except replay.InvalidMove:
                return {"legal": False, "invisible_paper": k, "at_old_move": i}
        bad = g.display() ^ inp.target[inp.requests[r]]
        return {"legal": True, "wrong_windows": [j for j in range(inp.n) if bad >> j & 1], "moves": g.moves}

    states = []
    for path in (before, after):
        g = replay.Game(inp, out.designs)
        g.order = start.copy()
        for k, d, label in path: g.move(k, d)
        assert g.finish(r)
        states.append(g)
    relevant = sorted({k for k, d, label in example["removed"] + example["added"]})
    example = {k: v for k, v in example.items() if k != "start_order"}
    example["delete_one"] = [{"index": i, "paper": before[i][0], **deletion({i})} for i in removed]
    example["delete_all_removed"] = deletion(set(removed))
    example["owners"] = {str(k): [{"position": g.position(k), "windows":
                                   [j for j in range(inp.n) if g.exposed_of(k) >> j & 1]} for g in states]
                         for k in relevant}
    return example


if __name__ == "__main__":
    folder = Path(__file__).resolve().parent
    chosen = [(45, 177), (0, 460), (2, 318), (1, 461), (2, 218)]
    with (replay.runs_dir() / ".lock").open("rb") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        analysis = json.loads((folder / "analysis-strong.json").read_text())
        run = replay.resolve_run(analysis["run"])
        examples = {(e["seed"], e["r"]): e for e in analysis["examples"]}
        result = [details(examples[key], run) for key in chosen]
    (folder / "examples.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))
