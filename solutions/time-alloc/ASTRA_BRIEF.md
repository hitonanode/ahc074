# Task for Astra 1: re-balance the time budget of the solver (time-alloc)

The user asks:

> いったん、ソルバー内の時間配分を調整し、実行時間を現状から延ばさない想定で、スコアがよりよくなるように
> してもらえますか。あくまで時間配分の調整（反復回数の修正など）のみを行ってください。

So: only budget changes (iteration counts, search budgets, numbers of candidates or rounds). No
algorithm changes. The judge run time must not grow. The goal is a better score.

## Rules (as before)

- Run test cases only through `scripts/pahcer_run.py`. Record normal runs (no `--no-record`);
  fixed-design runs are never recorded.
- Work in `solutions/time-alloc/` and sibling `solutions/time-alloc-*` directories (check
  `ls solutions` first). Japanese README per directory. No commits.
- Keep all logs, metrics, switches and profilers.

**Base: `solutions/esw-memo/main.cpp`** (merged as PR #134; the current best). Its designs are saved
in `20261105-130708_esw-memo`.

**Environment variables reach every solution in a `--compare`, including the base.** esw-memo reads
`F3_*`, `MAP_ITERS`, `GOPT_STEPS`, `ANNEAL_ITERS`, `CLIMB_ITERS`, the COLMDP_* names and others. So
compare variants as separate directories with the values hard-coded (or with new, private
environment names), never by setting esw-memo's names in a compare.

## The time constraint: the judge-time model

Use the judge-time model fitted to the user's submission (esw-climb4: 31 of 50 TLE):

    judge ≈ 1.04 × helper_end_sec + 1.35 × req_sec + (end_sec − helper_end_sec − req_sec)

The local stderr times are already scaled by CLOCK_SCALE 1.1.

- esw-memo: mean about 1.60 s, p99 about 1.76 s on calm runs.
- A candidate must not exceed the base's mean and p99 of this model, measured in the same normal
  compare (allow about +0.005 s of noise on the mean).
- Note: one local second of request time costs 1.35 judge seconds, one second of design 1.04.

## Knobs (budgets only)

- **Design**, section "Design iteration counts":
  - kMapIters 450000 and kGoptSteps 133000 (window assignment and its climb);
  - kAnnealIters 14.9M (design annealing, kAnnealSegments 4);
  - kClimbIters 154000 (filler climb);
  - kMatchIterations 4 (head-aware reassignment rounds).
- **Requests:**
  - the SearchConfig budgets, read through `search_env` (F3_*): `MODE` presets, `NS_ROUNDS`,
    `POST_CANDIDATES`, `PLAN_LIMIT`, `PLAN_EJECTS`, `ONE_ANCHORS`, `PLAN_SHORTLIST`, `REPEAT_MIN`,
    and the neutral width and slack (`NEUTRAL_WIDTH`, `NEUTRAL_SLACK`);
  - `kPostCandidates` (2), the number of plans post-processed.
- Hard-code the chosen values in the final `solutions/time-alloc/main.cpp`, so the submission needs
  no environment.

## Known marginal values (older bases; re-measure on esw-memo)

Normal 2000-seed compares unless noted:
- window assignment 2×: −0.154 ± 0.026% (+0.46 s);
- design annealing 2×: −0.075 ± 0.022% (+0.51 s);
- request search F2_MODE=2 (the 2× preset): −0.110% at +37% req time (fixed designs);
- kPostCandidates 2 → 4: −0.031% at +10% req time (fixed designs).

Per judge second, the request search looked most valuable and the design annealing least.
Moving anneal time to request search was the expected win. Measure before trusting this.

## Method (suggested)

1. **Request-side marginal values** on fixed designs:
   ```sh
   scripts/pahcer_run.py --compare solutions/esw-memo solutions/time-alloc-X --design-from 20261105-130708_esw-memo --seeds 0-200 --orders 2 -c "..."
   ```
   SE about 0.01% at 200 × 2 and 0.003% at 2000 × 2. Record score vs req_sec for a few budget levels
   (e.g. MODE=2, POST_CANDIDATES 4, NS_ROUNDS 2, kPostCandidates 3 / 4).
2. **Design-side marginal values** with normal compares: reduced anneal / map / climb iterations,
   e.g. 0.6× and 0.8×. 500 seeds first (SE about 0.05%), then 2000 (SE about 0.026%).
3. Choose the allocation that equalizes the marginal value per judge second within the constraint.
4. Confirm the final candidate with a normal 2000-seed compare against esw-memo. Show the score
   difference ± SE, W/T/L, and the judge-model mean / p99 / max of both arms.
   - The user wants a better score at no longer run time. If no allocation beats the base by ≥ 2 SE,
     report that clearly.

## Report

- `solutions/time-alloc/REPORT.md` in Japanese:
  - the marginal values measured;
  - the chosen allocation (old → new values);
  - the final results with run-ids.
- Final message: a 10-line summary.
