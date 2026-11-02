#!/usr/bin/env python3
"""Run the unchanged repository evaluator with an explicit local worker count.

  python3 solutions/chatgpt-study/run_compare.py --workers 3 \
      --compare solutions/imp-combo solutions/<candidate> --seeds 0-500 --no-record -c 'experiment'

The evaluator's existing template has threads=0 (os.cpu_count()). Python 3.12
does not offer -X cpu_count, so this process-local override supplies that default
without modifying pahcer_config.toml or scripts/pahcer_run.py. --compare and
--extend retain their ordinary scheduling, compilation and run recording.
"""
import argparse
import json
import os
from pathlib import Path
import runpy
import sys


def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--workers", type=int, default=3)
    args, forwarded = parser.parse_known_args()
    if args.workers < 1:
        parser.error("--workers must be positive")
    if not any(flag in forwarded for flag in ("--compare", "--extend", "--help", "-h")):
        parser.error("Use --compare or --extend; the single-run mode needs the pahcer executable")
    root = Path(__file__).resolve().parents[2]
    invocation = {"study_workers": args.workers, "reported_cpu_count": os.cpu_count(),
                  "arguments": forwarded,
                  "iteration_environment": {name: os.environ.get(name) for name in
                      ("MAP_ITERS", "GOPT_STEPS", "ANNEAL_ITERS", "CLIMB_ITERS")}}
    print("[chatgpt-study] " + json.dumps(invocation, ensure_ascii=False), flush=True)
    # Append the worker choice to the recorded run comment as well as the log.
    for flag in ("-c", "--comment"):
        if flag in forwarded:
            index = forwarded.index(flag)
            if index + 1 < len(forwarded):
                forwarded[index + 1] += f"; study_workers={args.workers}"
            break
    else:
        if "--help" not in forwarded and "-h" not in forwarded:
            forwarded += ["-c", f"study_workers={args.workers}"]
    os.cpu_count = lambda: args.workers
    sys.argv = [str(root / "scripts" / "pahcer_run.py")] + forwarded
    runpy.run_path(sys.argv[0], run_name="__main__")


if __name__ == "__main__":
    main()
