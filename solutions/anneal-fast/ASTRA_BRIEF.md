# Task 7 for Astra: exact speedups of the design stage after the window assignment (anneal-fast)

Same rules as before: test cases only through `scripts/pahcer_run.py ... --no-record`, small `--seeds`
ranges while developing, edit only inside `solutions/anneal-fast/`, no commits, no edits to
`scripts/`, `pahcer/`, other solutions or `trial_log.md`. Evaluations are serialized by a lock and two
other agents also evaluate, so expect waits; never run the solution or the tester directly on many
cases.

## Why

The user submitted esw-climb4 (= climb4-fast without your request speedups) and 31 of 50 cases hit
the 2 s limit (TLE). A model fitted to that result: judge time ≈ 1.04 × local design time + 1.35 ×
local request time (local times are the stderr `*_sec` values, already multiplied by CLOCK_SCALE
1.1). climb4-fast's mean is about 2.00 s on the judge, so it needs about 0.3 s less.

The request search is the most valuable time per second (F2_MODE=2: −0.110% for +0.15 s), so we cut
the design instead. Measured value of the design stages (2000-seed normal compares, run
20261105-064212):
- doubling the window assignment iterations: −0.154 ± 0.026%;
- doubling the design annealing iterations: −0.075 ± 0.022%.

Exact speedups lose nothing. The saved time either removes the TLEs, or later buys iterations.

Your fast3 (−0.009% at the same time on 2000 × 2) will be merged into the main line. Thank you.

## Goal

Create `solutions/anneal-fast/main.cpp` from a copy of `solutions/climb4-fast/main.cpp`. Make the
design stages AFTER the window assignment as fast as possible, with byte-identical output for every
input: the same random sequences, the same decisions, and the same floating-point results wherever
they affect a decision.

Local mean times (scaled; 2000 seeds, run 20261105-062119_climb4-fast), cumulative stderr metrics:

| metric | mean | stage it closes |
|---|---|---|
| `map_end_sec` | 0.705 | window assignment (not yours) |
| `anneal_end_sec` | 1.256 | Design annealing: 14.9M iterations, 0.551 s |
| `climb_end_sec` | 1.283 | filler climb: 0.027 s |
| `match_end_sec` | 1.364 | head-aware reassignment (Hungarian): 0.081 s |
| `perforation_end_sec` | 1.393 | handle perforation: 0.029 s |
| `helper_end_sec` | 1.433 | helper tables: 0.040 s |

Sections: `// ==== Design: units, columns and the cost model ====` through the helper tables and the
`design_papers` parts.

**Do not touch the window assignment.** That is `assign_windows` and what it uses: PosetSums,
WindowRelations, WindowPairs, evaluate_move, matching_cost, the screens. Another agent is doing
exact speedups there in `solutions/design-fast`, and the two diffs must merge cleanly onto
climb4-fast.

Profile first. Then remove the largest costs exactly: incremental cost updates, data layout,
avoiding allocations and recomputation, SIMD, and caches with exact keys.

## Measure

```sh
scripts/pahcer_run.py --compare solutions/climb4-fast solutions/anneal-fast --seeds 0-200 --no-record -c "..."
```

- Normal compare: no `--design-from`, because that skips the design stage.
- Byte-compare `runs/<run-id>_climb4-fast/out/*.txt` with `runs/<run-id>_anneal-fast/out/*.txt`. All files must be identical, all scores tied, WA 0.
- Report the means of `map_end_sec`, `anneal_end_sec`, `climb_end_sec`, `match_end_sec`, `perforation_end_sec`, `helper_end_sec` and `end_sec` for both arms of the same compare, and the per-stage time ratios. Only same-run ratios count.
- Confirm the final version on `--seeds 0-1000` (identical outputs).
- Keep CLOCK_SCALE, LOCAL_BENCH, the DesignStore, the @paper/@ops output, and the section markers with the table of contents.

## Report

- `solutions/anneal-fast/REPORT.md`, plus a Japanese `README.md` (first line `改良元: solutions/climb4-fast`, then what changed and why it is exact): the profile before/after and each speedup with its effect.
- Final message: a 10-line summary with the key numbers (per-stage times before/after and ratios, seeds verified identical, run-ids).
