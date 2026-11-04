"""Read saved runs only: verify moves, labels and neutral witnesses, then summarize the comparison.

Usage: python3 -B solutions/neutral-port/verify_results.py RUN BASE [--require-equal] [--require-traces]
The global evaluation lock prevents this serial replay from competing with an evaluation.
"""

import argparse
import fcntl
import json
import math
from pathlib import Path
import re
import statistics
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import replay


def verify(run, base, require_equal, require_traces):
    cases = replay.run_cases(run)
    reference = replay.run_cases(base)
    rows, counters, witnesses = [], {}, []
    equal = trace_count = 0
    trace_pattern = re.compile(r"#neutral (\d+) (\d+) ([^ ]*) ([^ ]*) ([^ ]*)")
    for seed, case in sorted(cases.items()):
        inp = replay.load_input(seed)
        raw = replay.out_path(run, seed).read_bytes()
        text = raw.decode()
        out = replay.parse_output(inp, text)
        assert not out.error and len(out.queries) == inp.r, (seed, out.error)
        same = raw == replay.out_path(base, seed).read_bytes()
        equal += same
        if require_equal:
            assert same, (seed, "stdout differs")
        err = replay.err_path(run, seed).read_text()
        stats = replay.stderr_stats(err)
        base_stats = replay.stderr_stats(replay.err_path(base, seed).read_text())
        assert case["score"] > 0 and stats["self_wrong"] == stats["op_label_errors"] == 0, seed
        assert base_stats["self_wrong"] == 0 and reference[seed]["score"] > 0, seed
        ann = replay.parse_annotations(err, inp.k)
        assert len(ann.ops) == inp.r and not replay.check_annotations(ann, out), seed
        traces = {}
        for line in err.splitlines():
            if not line.startswith("#neutral"):
                continue
            match = trace_pattern.fullmatch(line)
            assert match and "=" not in line, (seed, line)
            r, u = int(match[1]), int(match[2])
            assert r not in traces and 0 <= r < inp.r and u == inp.requests[r], (seed, r)
            paths = [[tuple(map(int, move.split(":"))) for move in part.split(",")] if part else []
                     for part in match.group(3, 4, 5)]
            assert paths[2] == out.queries[r] and len(paths[2]) < len(paths[0]), (seed, r)
            traces[r] = paths
        game = replay.Game(inp, out.designs)
        for r, path in enumerate(out.queries):
            if r in traces:
                for alternative in traces[r]:
                    trial = replay.Game(inp, out.designs)
                    trial.order = game.order.copy()
                    assert len(alternative) <= 2 * inp.k
                    for k, d in alternative:
                        assert 0 <= k < inp.k and 0 <= d < inp.k
                        trial.move(k, d)
                    assert trial.finish(r), (seed, r, "invalid witness display")
                trace_count += 1
                witnesses.append({"seed": seed, "r": r, "u": inp.requests[r],
                                  "lengths": [len(p) for p in traces[r]]})
            for k, d in path:
                game.move(k, d)
            assert game.finish(r), (seed, r, "wrong output display")
        assert game.score() == case["score"] == stats["total_moves"], seed
        assert reference[seed]["score"] == base_stats["total_moves"], seed
        for name, value in stats.items():
            if name.startswith(("neutral_", "triple_")):
                counters[name] = counters.get(name, 0) + int(value)
        rows.append({"seed": seed, "base": reference[seed]["score"], "candidate": case["score"],
                     "delta": case["score"] - reference[seed]["score"],
                     "log_ratio_percent": 100 * math.log(case["score"] / reference[seed]["score"]),
                     "req_sec": stats["req_sec"], "base_req_sec": base_stats["req_sec"],
                     "end_sec": stats["end_sec"], "execution_time": case["execution_time"]})
    if require_traces:
        assert trace_count > 0, "no trace witnesses"
    ratios = [r["log_ratio_percent"] for r in rows]
    n = len(rows)
    result = {"run": run.name, "base_run": base.name, "cases": n, "same_stdout_cases": equal,
              "total_base": sum(r["base"] for r in rows), "total_candidate": sum(r["candidate"] for r in rows),
              "log_ratio_percent_mean": statistics.mean(ratios),
              "log_ratio_percent_se": statistics.stdev(ratios) / math.sqrt(n) if n > 1 else None,
              "win_tie_loss": [sum(r["delta"] < 0 for r in rows), sum(r["delta"] == 0 for r in rows),
                               sum(r["delta"] > 0 for r in rows)],
              "req_sec_mean": statistics.mean(r["req_sec"] for r in rows),
              "base_req_sec_mean": statistics.mean(r["base_req_sec"] for r in rows),
              "req_sec_max": max(r["req_sec"] for r in rows),
              "end_sec_max": max(r["end_sec"] for r in rows), "counters": counters,
              "verified_requests": n * 1024, "verified_traces": trace_count,
              "witnesses": witnesses, "per_seed": rows}
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run")
    parser.add_argument("base")
    parser.add_argument("--require-equal", action="store_true")
    parser.add_argument("--require-traces", action="store_true")
    args = parser.parse_args()
    with (replay.runs_dir() / ".lock").open("rb") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        verify(replay.resolve_run(args.run), replay.resolve_run(args.base), args.require_equal, args.require_traces)
