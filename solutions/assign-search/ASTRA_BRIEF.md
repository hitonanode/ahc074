# Task 10 for Astra: a more efficient window-assignment search (assign-search)

The user asked for a focused effort on this: "かなり上がり目ありそうなので、注力してやってください" (it looks
like there is a lot of upside; please concentrate on it).

## Rules (changed: record the runs)

- Run test cases only through `scripts/pahcer_run.py`. Never run the solution or the tester directly
  on many cases. Evaluations are serialized by a lock and I also evaluate, so expect waits.
- **Do not use `--no-record` any more.** The user wants every evaluation to appear in `pahcer list`,
  even small `--seeds` checks. The only exception is a measurement-only build that exceeds the time
  limit (e.g. 2× iterations): it would set per-case best scores the real solution cannot reach.
- Edit only inside `solutions/assign-search/` (create sibling directories `solutions/assign-search-*`
  if you need several variants, after checking `ls solutions` for name clashes). No commits; I
  commit and open the PRs. No edits to `scripts/`, `pahcer/`, other solutions or `trial_log.md`.
- Each solution directory needs a Japanese README.md:
  - first line: 改良元: solutions/<base>;
  - the differences;
  - the switches and stderr metrics.
- Keep CLOCK_SCALE, LOCAL_BENCH, the DesignStore, the `@paper` / `@ops` output, all existing stderr
  metrics, profilers and experiment switches, and the section markers with the table of contents.
  The user explicitly wants logs and analysis facilities kept.

## The base and why this matters

**The base.** `solutions/esw-clean/main.cpp` is the new best (main). It is esw-speed cleaned without
any change of behavior. It includes the exact window-assignment speedups of `solutions/design-fast`
(map 0.676 → 0.463 s); read their `README.md` and `REPORT.md`. Judge-time model: mean 1.60 s,
p99 1.76 s. The window assignment is about 0.46 s local (scaled), the design annealing about 0.51 s.

**Why it matters:**
- gobj (assign_windows' objective: the mean cost of 71 greedily matched valid close pairs) is causal.
  Lowering it by any means improves the design at about 3% of the score per unit of gobj; doubling the
  iterations gave −0.052 gobj and −0.154 ± 0.026% on 2000 seeds.
- gobj_after on seeds 0–199 is 9.859 at 1×, 9.807 at 2×, 9.772 at 4× and 9.744 at 8× the
  iterations. 8× would be worth about −0.35%. This is the largest known lever in the whole solution.
- So the goal is a lower gobj at the same map time, through algorithmic changes. The user does not
  want mere parameter tuning (temperature schedule, move-type rates, stall limits) as the source of
  the gain.

## Facts

From the design-fast profile, per seed:
- 582k iterations, 84.6k ± 10k exact evaluations, 6.6k ± 0.8k acceptances.
- About 3430 close pairs (distance ≤ 26), but only about 160 valid (acyclic) at any time. The greedy
  scans about 133 of them to match 71, so the matching is limited by validity.
- After design-fast, about 1590 M cycles per seed (0.44 s). The largest parts:
  - the SIMD loop of evaluate_move over all 3430 pairs at every evaluation, about 340;
  - matching_cost, about 340;
  - the pending closure stage, about 240.
- The map time varies by case mainly through the number of exact evaluations and acceptances.

What failed:
- Evaluating only on a pool of the currently valid low-key pairs (solutions/map-pool): gobj 9.859 →
  10.134. The pairs that a move makes valid are the good moves; the validity of all close pairs must
  be tracked.
- 2–3 independent restarts in the same time (old): worse.

Your stopped task 8 had begun profiling and two prototypes ("orientation", "handle-rank") with no
conclusion yet. Its files are gone; start fresh from esw-clean.

## Directions (yours to choose and combine)

- **Targeted proposals.**
  - Make specific cheap invalid pairs valid. A pair's relation is a set of arcs between the 6 sheets,
    and a cycle can be broken by changing one window's edge or polarity, or by swapping a generic window
    with a handle window.
  - Move the remaining handle differences of the selected pairs into the generic set.
- **Incremental evaluation.** Recompute only the pairs that differ on the changed windows, instead of
  scanning all 3430 pairs. Update the greedy matching incrementally where it is exact, or verify cheaply.
- **Better neighborhoods or compound moves** that the random proposals rarely find. Evaluate several
  proposals that share work.
- **Elite or path-relinking strategies**, only if they beat a single long run at equal time.

The exact matching is my part: I am testing the exact min-cost matching from the user's
`biglib/maximum_weight_matching` in the objective and in Design::initialize myself. Do not spend
effort on it, but use my result if I send it.

## Measure

1. **gobj.** gobj_after (stderr) on seeds 0–199 is deterministic. Compare at equal map time: the mean
   `map_end_sec` of both versions in the same compare. Adjust your iteration counts to match if your
   iteration is cheaper or dearer.
   ```sh
   scripts/pahcer_run.py --compare solutions/esw-clean solutions/assign-search --seeds 0-200 -c "..."
   ```
2. **Score.** For a promising version: the same compare on `--seeds 0-500`. If the difference is
   negative, extend to 2000 seeds with `--extend <base run> <candidate run>`. Expect about 3% per unit
   of gobj; report the score difference ± SE and W/T/L.
3. Check WA 0, `self_wrong = 0`, `op_label_errors = 0`, and the end_sec distribution (no new 2 s
   overruns).

## Report

- `solutions/assign-search/REPORT.md`:
  - the analysis of the search;
  - each idea with its gobj at equal map time;
  - the score results with run-ids.
- Final message: a 10-line summary with the key numbers.

Report in Japanese where the user reads it (README, REPORT); the final message may be Japanese or
English.
