"""Validate saved outputs, including alternative order sequences, without running a solver."""
import argparse
import fcntl
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import replay


def verify(run):
    total_moves = requests = cases = 0
    for seed, record in sorted(replay.run_cases(run).items()):
        for j, score in enumerate(record.get("order_scores", [record["score"]])):
            directory = run if j == 0 else run / "orders" / str(j)
            # pahcer_run.py's ORDERS_VERSION=v1, recorded in this experiment's evaluation code.
            inp = replay.load_input(seed) if j == 0 else replay.parse_input(
                (replay.runs_dir() / ".orders" / "v1" / str(j) / f"{seed:04d}.txt").read_text())
            out = replay.parse_output(inp, replay.out_path(directory, seed).read_text())
            err = replay.err_path(directory, seed).read_text()
            ann = replay.parse_annotations(err, inp.k)
            stats = replay.stderr_stats(err)
            assert not out.error and not replay.check_annotations(ann, out), (seed, j)
            assert score > 0 and stats["self_wrong"] == stats["op_label_errors"] == 0
            game = replay.Game(inp, out.designs)
            generic = [k for k, role in enumerate(ann.papers["role"]) if role == "generic"]
            for r, moves in enumerate(out.queries):
                for k, d in moves:
                    game.move(k, d)
                assert game.finish(r), (seed, j, r)
                cap = game.order.index(0)
                assert all(game.order.index(k) > cap for k in generic), (seed, j, r, "cap")
            assert game.score() == score, (seed, j, game.score(), score)
            total_moves += game.moves
            requests += game.completed
            cases += 1
        if seed % 10 == 9:
            print(f"verified through seed {seed}", flush=True)
    return {"run": run.name, "cases": cases, "requests": requests,
            "moves": total_moves, "wrong": 0, "annotation_errors": 0, "cap_errors": 0}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    print("Waiting for the evaluation lock before saved-output replay.", flush=True)
    with (replay.runs_dir() / ".lock").open("rb") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        result = verify(replay.resolve_run(args.run))
    Path(args.output).write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result), flush=True)
