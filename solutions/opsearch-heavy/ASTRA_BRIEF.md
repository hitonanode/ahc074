# Task 2 for Astra: heavy per-request search, what it finds, and an efficient search

(Continuation of your port `solutions/neutral-port`; same rules as before: run test cases only via
`scripts/pahcer_run.py ... --no-record` (it takes the global lock; keep `--seeds` ranges small, at most
100 seeds per run), edit only inside the new directories named below, no commits, no edits to
`scripts/`, `pahcer/`, other solutions or `trial_log.md`. Fixed designs: `--design-from
20261104-224750_esw-fixiter`.)

## Goal

Your port showed that the order processing still has room: neutral 2→2 rewrites + re-shortening gave
−0.38% total moves on 25 fixed-design seeds, at 3.85× request time. We want to know (1) how much
better per-request move sequences a much heavier search finds, (2) what those better sequences look
like compared with the current ones (which moves disappear, which appear, why the current
post-processing cannot reach them), and (3) a search that finds most of that gain cheaply.

## Step 1: `solutions/opsearch-heavy/main.cpp` (copy of `solutions/neutral-port/main.cpp`)

A research version with no time limit concern (it is never submitted). Add environment knobs (read
once; defaults = neutral-port's behaviour) for a heavier search, for example:
- `NS_ROUNDS` (default 1): iterate the neutral phase — collect neutral candidates from the current
  best, re-shorten each, keep the best; repeat while it improves (or a fixed number of rounds,
  including walks over equal-cost candidates with a tabu on visited signatures if useful).
- larger `NEUTRAL_WIDTH` / `NEUTRAL_SLACK`; more re-shortening rounds per candidate.
- `POST_CANDIDATES` (default 2 = kPostCandidates): more distinct plans fully post-processed.
- new rewrite operators of your choice that the current code cannot reach, e.g. 1→1 (delete one move
  and add one repair move, kept as a neutral candidate), 3→3 / 3→2, repair moves inserted at the
  times when the repair paper is visible (as `eject_repairs` does) instead of only at the end,
  changing the anchor of two moves jointly, etc.
Choose the operators by reasoning about the structure (papers, columns, handles, fillers, the
comparator), not by brute force alone; every candidate must still pass the existing `evaluate`
checks (legality, display, cap invariant, fillers reachable), and the objective stays `plan_cost`.

Instrumentation under LOCAL_BENCH (no `=` on these lines; prefix `#heavy`): for every request whose
final sequence differs from what plain esw-fixiter post-processing would have returned **from the same
start state** (keep a copy of that sequence before your phase), print the request, u, both sequences
with the move labels (`paper:depth:label`, output paper numbers as in main; labels from `op_tags`,
new moves `repair`), both `plan_cost`s, and which operator / round produced it.

## Step 2: measure (fixed designs)

On `--seeds 0-48` (one order sequence), report for a ladder of settings (from neutral-port's default
up to something like 30–100× esw-fixiter's request time): total moves vs esw-fixiter (sum, per-seed
log-ratio mean ± SE), mean `req_sec`. Use `--compare solutions/esw-fixiter solutions/opsearch-heavy`
with the knobs as environment variables (they are passed to every compared solution; esw-fixiter
ignores them). Keep each run's wall time reasonable (≤ 10 minutes per run).

## Step 3: look at the improvements

From the `#heavy` traces of the strongest setting (a few thousand improved requests), classify the
transformations: how many moves removed / added, the labels of the removed and of the added moves
(e.g. a dig + the return of the dug paper disappear; a filler is replaced by another paper; a
helper replaces generic moves; ...), the columns involved, whether the improvement is in the move
count or only in the end-state value (plan_cost terms), which operator and round found it, and which
cheap signal (available before the expensive re-shortening) would have predicted that a candidate
leads to an improvement. Show 3–5 concrete examples with explanations.

## Step 4: an efficient search

Using step 3, design and implement `solutions/opsearch-fast/main.cpp` (copy of neutral-port or of
your heavy version): a search that keeps most of the heavy gain at a small cost — target: request
time at most about 1.5× esw-fixiter's (req_sec ≈ 0.24 s locally), and as much of the gain as
possible. Measure it the same way (seeds 0-48, then 0-100 with `--orders 2` if promising), and keep
`NEUTRAL=0`-style switches so that the base behaviour is reproducible.

## Report

`solutions/opsearch-heavy/REPORT.md`: the operators, the ladder (moves and time per setting), the
classification with examples, the cheap predictors, and the fast version's result. Japanese
`README.md` in each new solution directory (base solution, differences, knobs, stderr counters).
Final message: a 15-line summary with the key numbers.
