# Task 6 for Astra: a smarter neutral search at the same time (opsearch-fast3)

Same rules as before: test cases only through `scripts/pahcer_run.py ... --no-record`, small `--seeds`
ranges while developing, edit only inside `solutions/opsearch-fast3/`, no commits, no edits to
`scripts/`, `pahcer/`, other solutions or `trial_log.md`. Evaluations are serialized by a lock and
another agent also evaluates, so expect waits; never run the solution or the tester directly on
many cases.

## Situation

- The new best is `solutions/climb4-fast` (merged): esw-climb4 + your colmdp-fast exact speedups. On
  2000 normal seeds its output is identical to esw-climb4; req_sec 0.383 → 0.357 s.
  - Its request processing = your opsearch-fast2 (F2_MODE=1) + the column subsequence MDP in the
    state value + the colmdp-fast speedups.
  - The designs of run `20261105-062119_climb4-fast` are saved (use them with `--design-from`).
- Measured headroom of the same neighborhoods under the column-MDP value (trial_log.md, 2026-11-05
  sections):
  - F2_MODE=2: −0.110 ± 0.005% at +37% request time (fixed designs, 200 seeds × 2 orders).
  - `solutions/heavy-mdp` (your opsearch-heavy + the column MDP) with NS_ROUNDS=5
    NEUTRAL_WIDTH=48 NEUTRAL_SLACK=2 NS_SHORT_ROUNDS=6 POST_CANDIDATES=8 NS_TRIPLES=1:
    −0.283 ± 0.025% at 11× the time (48 seeds).
  - Post-processing 4 plans instead of 2 (kPostCandidates): −0.031 ± 0.004% at +10%.
  - The state value is calibrated in the direction the neutral search uses: 88% of the predicted
    gains are realized (`solutions/valprobe`).
- Time is binding. There is no fallback (removed on purpose). Locally, end_sec exceeds 2.0 s in
  22/2000 seeds and 1.9 s in 197/2000. The judge's request processing is slower than local. Any
  gain must therefore come at (nearly) the same request time.

## Goal

`solutions/opsearch-fast3/main.cpp`, starting from a copy of `solutions/climb4-fast/main.cpp`:

- a lower score at a req_sec ratio ≤ 1.03 versus climb4-fast, both measured in the same `--compare`.

The user explicitly does not want mere parameter or budget tuning: no raising of rounds, widths,
slack or candidate counts, and no retuning of constants as the source of the gain. Keep plan_cost
(the objective) unchanged; this task is about the search. Improvements must come from how the search
spends its time, for example:

- **Profile time against yield.** Measure where the current search's time goes versus where its
  accepted improvements come from: per operator, stage, round, candidate rank and request type.
  Remove or short-circuit work that almost never pays, and reinvest into work that pays.
- **Spend adaptively.** Predict per request (or per candidate) whether more search is likely to pay,
  from cheap signals available before or early in the search. Examples: the number of same-length
  alternatives, the gaps in plan_cost between plans, the first round's gain.
- **Generate what heavy finds.** On the same start states, compare heavy-mdp's accepted changes
  with climb4-fast's: which improvements does heavy find that fast2 misses, and what pattern do they
  have? Then generate those rewrites directly instead of enumerating more broadly.
- **Screen cheaply, verify exactly.** Use bounds that let you skip candidates that cannot beat the
  incumbent.

## Switches

Every solution in a `--compare` receives the environment variables. climb4-fast reads `F2_<name>`
and then the plain `<name>` (search_env). Give your copy's switches a new prefix (for example `F3_`)
so that settings meant for fast3 never reach the baseline. Do not set F2_* or plain names in
compares.

## Measure

```sh
scripts/pahcer_run.py --compare solutions/climb4-fast solutions/opsearch-fast3 --design-from 20261105-062119_climb4-fast --seeds 0-200 --orders 2 --no-record -c "..."
```

- Report the mean log ratio ± SE, wins/ties/losses, and the req_sec of both arms with their ratio.
- If the 200 × 2 result is clearly negative at the time limit above, confirm on 2000 seeds × 2
  orders.
- Then run a normal compare (no `--design-from`) on 200 seeds for WA = 0, `self_wrong = 0`,
  `op_label_errors = 0` and the end_sec distribution.
- Keep the analysis output (@paper / @ops labels), the section markers with the table of contents,
  LOCAL_BENCH, CLOCK_SCALE and the DesignStore.

## Report

- `solutions/opsearch-fast3/REPORT.md`, plus a Japanese `README.md` (base solution and the
  differences): the time/yield profile before the change, what was changed and why, and the results
  (200 × 2, 2000 × 2, and the req_sec ratios).
- Final message: a 10-line summary with the key numbers.
