# Task 3 for Astra: a stronger cheap search (continuation of opsearch-heavy / opsearch-fast)

Same rules as before (test cases only through `scripts/pahcer_run.py ... --no-record`, small `--seeds`
ranges while developing, edit only inside your new directory, no commits, no edits to `scripts/`,
`pahcer/`, other solutions or `trial_log.md`; fixed designs `--design-from 20261104-224750_esw-fixiter`).
I am running a 2000-seed check of neutral-port and opsearch-fast myself; you do not need to.

## Goal

Your heavy search reached −0.54% total moves (48 seeds) at 43× request time and opsearch-fast keeps
about half of it (−0.26% on 100 seeds × 2 orders) at 1.53×. Build `solutions/opsearch-fast2` (copy
your opsearch-fast) that keeps clearly more of the heavy gain at a similar cost. Two budgets, both
measured as mean `req_sec` relative to esw-fixiter in the same `--compare` run:

1. at most 1.5×: maximise the gain;
2. at most 2.0×: maximise the gain.

Report the best configuration for each budget (env knobs are fine; make the 1.5× one the default).

## Directions (your choice; use your own analysis in REPORT.md as the guide)

- The per-request time is dominated by `evaluate` replays inside `post_optimize` and by full edit /
  eject passes on candidates. Exact speedups (same outputs, cheaper replays: incremental prefix
  covers, reuse of the replay of a common prefix between trials, cheaper legality checks, avoiding
  repeated anchorize / canonicalize, early rejection by the display filter) buy search budget.
  Verify any exact speedup by byte-identical stdout on 25 seeds against the version before it.
- Spend the budget where the heavy gains came from: alternative plans fully post-processed
  ("別計画の完全短縮", 564 of 1661 shortened requests), direct 3→2 (375), direct 2→2 (313), 2→2
  candidates re-shortened (275), 1→1 (38 + 43). Cheap screens that predict which alternative plan /
  which deletion pairs can win (your table: re-moved papers capture 93% of the shortening; candidates
  already shorter at collection succeed 24%) can cut most of the work.
- Prefer orderings that try the most promising candidates first and stop early.

## Measure

`--compare solutions/esw-fixiter solutions/opsearch-fast solutions/opsearch-fast2 --design-from
20261104-224750_esw-fixiter --seeds 0-100 --orders 2 --no-record` (and smaller ranges while
developing). Correctness as before: no WA, `self_wrong = 0`, `op_label_errors = 0`, `NEUTRAL=0`
byte-identical to esw-fixiter on 25 seeds.

## Report

`solutions/opsearch-fast2/REPORT.md` (+ Japanese `README.md`): what changed, the exact speedups and
their verification, the ladder (gain vs req_sec ratio) with run-ids, the two recommended settings.
Final message: a 12-line summary with the key numbers.
