# Task 4 for Astra: steer the design annealing towards designs with good column heads

Same rules as before (test cases only through `scripts/pahcer_run.py ... --no-record`; edit only inside
`solutions/head-steer/`; no commits; no edits to `scripts/`, `pahcer/`, other solutions,
`trial_log.md`). This task changes the DESIGN, so the order-processing-only shortcut
(`--design-from` of one saved design) does not apply; how to measure is below.

## What we measured (dsel-probe, trial_log.md 2026-11-05; read that section first)

- Same case, different design random seeds: the true quality of the design varies with sd 0.44%
  (window assignment and design annealing both contribute: sd 0.42% with only the assignment's seed
  changed, 0.34% with only the annealing's; rematch + perforation 0.05%). The effect is a steady
  state property, 77% of it in the `fix` moves (digs that set a handle's color), and it does not
  depend on the order processing (opsearch-fast sees the same design effects, r = 0.98).
- In this natural variation the realized moves follow `J = model_cost − 0.75·proxy` (r = 0.62)
  much better than `model_cost` (r = 0.44). `proxy` = Design::filler_climb's filler value of the
  column heads (per column and color, the head-color probability times the utility of the strongest
  eligible unit; utility = filler_gain summed over the targets), recomputed on the final design
  (`solutions/dsel-probe/proxy.py`). Per component: hole handling ≈ 0.98·model_hole − 0.77·proxy,
  digs ≈ 0.96·model_col, generic ≈ 1.02·model_gc.
- Optimizing it is delicate (Goodhart): `solutions/jclimb` (my broad climb on cur − λ·proxy after
  the filler climb: any-colour column swaps, unit moves, target exchanges, λ = 0.75) made designs
  WORSE by +0.05..+0.09%. But the existing restricted filler climb (swap two units of the same kind
  that keep both colours, accept if cur − λ·proxy decreases; esw-fixiter uses λ = 1.0) is causal:
  1000 seeds × 4 orders vs esw-fixiter: λ 0.75 −0.042%, λ 0.5 −0.072% (±0.012), λ 0.5 with 4×
  iterations −0.095%, λ 0.25 with 4× −0.079%, λ 0 with 4× +0.071% (the proxy is needed, at about
  half the weight). Choosing the better of two half-length annealings by J (λ 0.5) gave −0.04% vs one
  full annealing (selection works, halving the compute nearly cancels it).
- The annealing (Design::Annealer, 14.9M iterations in 4 segments) optimizes model_cost only; its
  final proxy is essentially random, and the later climbs only partly repair it.

## Goal

Make the design annealing itself prefer good heads, so that its designs land in high-proxy basins
without paying model cost, at (nearly) the same compute. One historical precedent: solutions/left-ap
(an older lineage) added a linearized filler proxy to its annealing (`AP_*`, from progress 0.5,
refreshed 4 times; −0.18% then). Ideas (your choice): a per-(unit, column) linearized head value
added to the cost of the moves that change columns, refreshed a few times per segment; the head
model of the climb (strongest eligible unit) or a smoother one; a small weight (the climb says the
causal weight is about half the regression weight); restricting the proxy term to moves of the safe
kind; etc. Keep the annealing fast (it is AVX2 code in Design::Annealer; a table lookup per moved
unit is affordable, a pass over the targets per move is not).

Also measured since: around λ 0.5 the climb weight is flat (λ 0.4 / 0.6: +0.010 / 0.000 ± 0.007% vs
0.5), while the reassignment weight (rematch_probability, 1.0) and the perforation weight (0.5) are
at their optima (RM_WEIGHT 0.75 / 1.25 / 1.5: worse / ±0 / +0.080%; PERF_WEIGHT 0.35 / 0.7: +0.037 /
±0%). A second, cheaper direction you may combine: the restricted climb improved further with 4×
iterations (λ 0.5: −0.072% → −0.095%), but costs about +0.12 s; it samples random pairs and rejects
most (same kind and both colours kept), so an exact-equivalent climb that enumerates only the
admissible pairs, or reaches a local optimum faster, may get that gain within the current time.

## How to measure (design changes)

Base for comparison: `solutions/dsel-probe` with `CLIMB_LAMBDA=0.5` (the new climb weight; it will be
part of the next solution). For a candidate `solutions/head-steer` (copy of dsel-probe, default
CLIMB_LAMBDA changed to 0.5 in your copy or passed by env):
1. `scripts/pahcer_run.py solutions/head-steer --seeds 0-200 --save-design --no-record -c "..."`
   (saves each design; also evaluates the real order sequence),
2. `scripts/pahcer_run.py solutions/head-steer --design-from <run of step 1> --orders 4 --seeds 0-200 -c "..."`
   (evaluates the saved designs on 4 order sequences; not recorded),
3. the base is already measured for seeds 0-999: designs `20261105-005904_dsel-probe`, orders-4
   run `20261105-010030_dsel-probe` (dsel-probe with `CLIMB_LAMBDA=0.5`); pair_compare.py uses the
   seeds common to both runs, so a 200-seed candidate run compares on those 200 seeds,
4. paired difference per seed: `/home/sato/ahc074/.venv/bin/python solutions/dsel-probe/pair_compare.py <base orders run> <candidate orders run>`
   (mean over the 4 order sequences of 100·log(candidate/base), mean ± SE over seeds).
With 200 seeds the SE is about 0.025%; go to 1000 seeds (`--seeds 0-1000`) for promising variants.
Also report the design time (`anneal_end_sec − map_end_sec` in the err files; must stay within
about +5% of the base) and the model_cost / proxy you get (proxy.py on the saved designs).

## Report

`solutions/head-steer/REPORT.md` (+ Japanese `README.md`): the method, the variants and their
results (with run-ids), time, and your recommendation. Final message: a 12-line summary.

## Scope reminder from the user (2026-11-05)

Only changes that genuinely improve the quality of the search or of the objective are wanted. Do not
run parameter sweeps for their own sake (a weight may be set by a principled argument or a coarse
check, but the contribution must be the mechanism). Report the mechanism and why it works.
