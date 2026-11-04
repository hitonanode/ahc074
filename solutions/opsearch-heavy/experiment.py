"""Run one locked pahcer comparison and retain its settings and paired statistics locally."""
import argparse
import fcntl
import json
import math
import os
from pathlib import Path
import re
import statistics
import subprocess
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import replay


def summarize(base_id, candidate_id):
    runs = [replay.resolve_run(x) for x in (base_id, candidate_id)]
    cases = [replay.run_cases(r) for r in runs]
    ratios, rows, timing, metrics = [], [], [[], []], [{}, {}]
    for seed in sorted(cases[1]):
        scores = [c[seed].get("order_scores", [c[seed]["score"]]) for c in cases]
        assert len(scores[0]) == len(scores[1]) and all(s > 0 for a in scores for s in a), seed
        ratios.append(statistics.mean(100 * math.log(c / b) for b, c in zip(*scores)))
        rows.append({"seed": seed, "base": scores[0], "candidate": scores[1], "log_percent": ratios[-1]})
        for arm, run in enumerate(runs):
            for j in range(len(scores[arm])):
                directory = run if j == 0 else run / "orders" / str(j)
                # All numeric summary lines are at the end. Do not parse millions of candidate
                # traces merely to read req_sec; this bounded read stays negligible beside a run.
                with replay.err_path(directory, seed).open("rb") as log:
                    log.seek(0, 2)
                    log.seek(max(0, log.tell() - 16384))
                    stats = replay.stderr_stats(log.read().decode())
                assert stats["self_wrong"] == stats["op_label_errors"] == 0, (arm, seed, j)
                timing[arm].append(stats["req_sec"])
                for name, value in stats.items():
                    if name.startswith(("ns_", "neutral_", "triple_")):
                        metrics[arm][name] = metrics[arm].get(name, 0) + value
    return {"runs": [p.name for p in runs], "seeds": len(rows), "orders": len(rows[0]["base"]),
            "totals": [sum(sum(r[key]) for r in rows) for key in ("base", "candidate")],
            "log_percent_mean": statistics.mean(ratios),
            "log_percent_se": statistics.stdev(ratios) / math.sqrt(len(ratios)) if len(ratios) > 1 else None,
            "win_tie_loss": [sum(x < 0 for x in ratios), sum(x == 0 for x in ratios), sum(x > 0 for x in ratios)],
            "req_sec_mean": list(map(statistics.mean, timing)), "req_sec_max": list(map(max, timing)),
            "time_ratio": statistics.mean(timing[1]) / statistics.mean(timing[0]), "metrics": metrics,
            "meta_summary": [json.loads((p / "meta.json").read_text())["summary"] for p in runs],
            "per_seed": rows}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("label")
    parser.add_argument("--candidate", default="solutions/opsearch-heavy")
    parser.add_argument("--base", default="solutions/esw-fixiter")
    parser.add_argument("--seeds", default="0-48")
    parser.add_argument("--orders", type=int, default=1)
    parser.add_argument("--env", nargs="*", default=[])
    args = parser.parse_args()
    env = dict(os.environ)
    settings = dict(item.split("=", 1) for item in args.env)
    env.update(settings)
    command = [str(ROOT / "scripts/pahcer_run.py"), "--compare", args.base, args.candidate,
               "--design-from", "20261104-224750_esw-fixiter", "--seeds", args.seeds,
               "--orders", str(args.orders), "--no-record", "-c", args.label + " " + " ".join(args.env)]
    folder = Path(__file__).resolve().parent / "experiments"
    folder.mkdir(exist_ok=True)
    with (folder / (args.label + ".log")).open("w") as log:
        proc = subprocess.Popen(command, cwd=ROOT, env=env, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True)
        lines = []
        for line in proc.stdout:
            print(line, end="", flush=True)
            log.write(line)
            lines.append(line)
        if proc.wait():
            raise SystemExit(proc.returncode)
    ids = re.findall(r"\[pahcer_run\] run-id: (\S+)", "".join(lines))
    assert len(ids) == 2, ids
    result = summarize(*ids)
    result.update({"label": args.label, "settings": settings, "command": command})
    (folder / (args.label + ".json")).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({k: result[k] for k in ("label", "runs", "totals", "log_percent_mean", "log_percent_se",
                                           "req_sec_mean", "time_ratio", "win_tie_loss")}, ensure_ascii=False))
