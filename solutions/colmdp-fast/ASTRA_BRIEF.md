# Task 5 for Astra: exact speedups of the request processing of esw-colmdp

Same rules as before (test cases only through `scripts/pahcer_run.py ... --no-record`; small `--seeds`
ranges while developing; edit only inside `solutions/colmdp-fast/`; no commits; no edits to
`scripts/`, `pahcer/`, other solutions, `trial_log.md`). Check `ls solutions` before creating any
directory: names must be new.

## Situation

The current best is `solutions/esw-colmdp` (merged to main): esw-fixiter's design (filler climb weight
0.5) + your opsearch-fast2 neutral search (F2_MODE=1) + the column subsequence MDP of PR 115
(solutions/colmdp, by another agent). Normal 2000-seed compare vs esw-fixiter: −0.695%. On fixed
designs the MDP adds −0.29% on top of fast2 (it adds only −0.10% to esw-fixiter): the neutral search
picks same-length sequences with a better end-state value, so a better value function pays off
three times more. A calibration probe (solutions/valprobe, trial_log 2026-11-05) showed the value
is well calibrated (88% of the predicted gains are realized), so the remaining room is in how many
candidates the search can examine per unit time.

The time limit is now binding: the time-shortage fallback (request pacing, light plan) was removed
on purpose, so every request runs the full search. Local full-effort runs (24 parallel) give
`req_sec` about 0.40 s and `end_sec` (CLOCK_SCALE 1.1) above 2.0 s in about 220 of 2000 seeds; the
judge is slower on request processing (about 1.35× the local scaled time). We need the request
processing about 30% faster before any further search can be afforded.

## Goal

`solutions/colmdp-fast/main.cpp` (copy of `solutions/esw-colmdp/main.cpp`): byte-identical stdout to
esw-colmdp on fixed designs, with request processing time (`req_sec`, measured in the same
`--compare` run) as low as you can get it; target at least 30% less. Same algorithm, same
candidates, same order of floating-point operations where it affects decisions (verify by
byte-identical outputs on at least 100 seeds × 2 orders). Profile first (where does the time go now
with fast2 + the column MDP: evaluate replays, canonicalize, plan_cost / adaptive_next_cost with the
MDP scan, run_plan simulations, helpers, chains, eject candidates, neutral candidates' edit passes,
...), then remove the largest costs. Your own previous exact speedups (exact-* in
solutions/opsearch-fast2) are the starting point; the MDP added new costs (colmdp_gap_values in
adaptive_insert, the MDP scan in adaptive_next_cost) that are worth looking at.

Optionally, if the request processing is done and time remains: the same for the design stages
(window assignment, annealing, filler climb, rematch, perforation, helper tables), whose iteration
counts are fixed (esw-fixiter: "Design iteration counts"); exact speedups there let us later raise
the counts at the same judge time.

## Measure

`scripts/pahcer_run.py --compare solutions/esw-colmdp solutions/colmdp-fast --design-from
20261104-224750_esw-fixiter --seeds 0-100 --orders 2 --no-record -c "..."` (check: all ties, no WA,
`self_wrong = 0`, `op_label_errors = 0`; report the mean `req_sec` of both arms and the ratio).
Under the 24-parallel load the time ratio is what counts (not a single-process timing).

## Report

`solutions/colmdp-fast/REPORT.md` (+ Japanese `README.md`): the profile before / after, each
speedup and its verification, the final req_sec ratio (100 seeds × 2 orders, and 300 seeds × 1 order
if time allows). Final message: a 10-line summary with the key numbers.
