"""Judge-time model of runs (trial_log 2026-11-05 ジャッジでの時間の模型):
judge ~= 1.04 x design end (helper_end_sec) + 1.35 x request planning (req_sec) + the rest (end_sec - both).
Prints the mean, 99% point and maximum of the model and of end_sec per run.

Usage: python judge_time.py RUN...
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import replay  # noqa: E402


def main():
    for arg in sys.argv[1:]:
        run = replay.resolve_run(arg)
        model, end = [], []
        for path in sorted((run / "err").glob("*.txt")):
            st = replay.stderr_stats(path.read_text(errors="replace"))
            if not {"helper_end_sec", "req_sec", "end_sec"} <= st.keys():
                continue
            h, q, e = st["helper_end_sec"], st["req_sec"], st["end_sec"]
            model.append(1.04 * h + 1.35 * q + (e - h - q))
            end.append(e)
        m, e = np.array(model), np.array(end)
        print(f"{run.name}: cases {len(m)}, judge model mean {m.mean():.4f} s, p99 {np.quantile(m, 0.99):.4f} s, "
              f"max {m.max():.4f} s; end_sec mean {e.mean():.4f} s, p99 {np.quantile(e, 0.99):.4f} s")


if __name__ == "__main__":
    main()
