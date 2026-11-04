# Task for Astra: port the "2→2 neutral rewrite + re-shortening" of PR 114 onto esw-fixiter

You work in the git worktree `/home/sato/ahc074/.claude/worktrees/esw-fixiter-improvement-55c629`
(the "repo" below). Read `CLAUDE.md` (in Japanese; the project rules) first.

## Background (short)

AtCoder Heuristic Contest 074 (reactive). 192 papers, 64 windows, 1024 orders; each order u we
output a sequence of moves (take a visible paper, insert it below depth d) so that the display
equals barcode A_u. Score = 384·(wrong orders) + (total moves); lower is better. Our best solution is
`solutions/esw-fixiter/main.cpp` (6725 lines; `grep -n '// ====' main.cpp` lists its parts). Its
design is deterministic (fixed iteration counts), and under `-DLOCAL_BENCH` the order processing
always uses full effort, so its output is a deterministic function of the input.

Per order, `Solver::process(u)` (part "Request processing (process)") builds candidate plans, keeps
the cheapest by `plan_cost(moves) = moves + filler_charge + kEndWeight·adaptive_next_cost`, then
post-processes it with `post_optimize` (part "Post-processing: deletions and new anchors of the
edits"; the edit pass with `eject=false`, and the eject pass with `eject=true`, which calls
`eject_repairs`: delete two edits and insert one repair move).

PR 114 (a report by another agent, on an older base `solutions/eject-single-window`) added a
"2→2 neutral rewrite + re-shortening" and reported −0.40% total moves on 20 fixed-design cases.
Its functional diff is `/tmp/claude-1000/-home-sato-ahc074--claude-worktrees-esw-fixiter-improvement-55c629/4b08d16a-e458-4ef7-a878-a32403e05bc1/scratchpad/pr114/docs/chatgpt-neutral-escape/neutral-escape-core.patch`
and its full description `.../scratchpad/pr114/docs/chatgpt-neutral-escape/README.md` plus the PR body
`.../scratchpad/prs/pr114_body.md` (Japanese; sections 5–7 describe the algorithm and the
interval bounds of the two-paper repair). Read all three.

Name mapping between the patch's base (eject-single-window) and esw-fixiter:
- `post_optimize_links(initial, input_ops, u, only_eject)` ↔ `post_optimize(initial, input_ops, u OP_TAG(, tags), eject)`
- `score(path.size())` ↔ `plan_cost(path.size())`; `mid_accepts` etc. ↔ `eject_accepts` etc.
- The patch's `std::vector<int> ord` replays ↔ esw-fixiter's byte-order helpers (`ByteOrder`,
  `find_paper`, `shift_byte`) and the linked-list replay used in `evaluate` / `eject_repairs`.
- esw-fixiter carries move labels under LOCAL_BENCH (`OP_TAG`, `Edit::tag`, `path_tags`): every
  saved candidate must keep the labels of its path; a newly inserted edit has the default tag
  `kOpRepair`. `op_label_errors` must stay 0.

## Deliverable 1: `solutions/neutral-port/main.cpp` (+ `README.md` in Japanese)

Copy `solutions/esw-fixiter/main.cpp` to `solutions/neutral-port/main.cpp` and port the patch's
behaviour faithfully:

1. In `post_optimize`'s `evaluate`, when a member flag `neutral_collect` is set: after the
   candidate passes `fillers_reachable()` and `value = plan_cost(path.size())` is computed, if
   `path.size() <= input_ops.size()`, `value <= best_score + kNeutralSlack` (0.75) and the final
   order differs from `seed.order`, store {state (save()), path, tags, value, signature} in
   `neutral_candidates`: signature as in the patch (hash of the papers that are the first or second
   opaque paper of some window, top-down); same signature → keep the lower value; keep at most
   `NEUTRAL_WIDTH` candidates (lowest value). This happens before the existing
   `if (value + 1e-8 >= best_score) return false;`.
2. In the eject branch of `post_optimize`, when `neutral_collect` is set and `edits.size() >= 2`,
   after the existing `eject_repairs`: the patch's 2-deletion + 2-move repair enumeration (for
   every pair x < y of the base edits: delete both, replay with visibility, if the display is
   already A_u just evaluate, else compute first/second/third opaque owners, the pool of papers
   that own a first or second opaque window (not the cap), and for every ordered pair (f, g) of the
   pool the interval bounds and the two tail moves, then `evaluate(trial + tails)`). Count
   `triple_trials / triple_repairs / triple_accepts`. Then `edits = anchorize(best_ops ...)` as the
   patch does. Keep the semantics; you may use esw-fixiter's faster replays.
3. In `process`, only when `effort == 0`, after the existing final eject loop: the patch's neutral
   phase — one more `post_optimize(..., eject=true)` with `neutral_collect = true`, then for each
   stored candidate: restore its state, `path = post_optimize(st0, path, u, tags, false)` if
   `NEUTRAL_DEPTH >= 2`, then up to 2 rounds {eject pass; break if no eject accept; edit pass},
   and keep it if `plan_cost(path.size())` is lower than the incumbent's (restore the incumbent's
   state at the end otherwise). Count `neutral_total, neutral_accepted, neutral_direct_saved,
   neutral_escape_saved` as the patch does.
4. Environment knobs (read once, as static locals): `NEUTRAL` (default 1; `NEUTRAL=0` disables every
   new code path, and the output must then be byte-identical to esw-fixiter), `NEUTRAL_WIDTH`
   (default 4), `NEUTRAL_DEPTH` (default 2; 0 = collect but do not re-shorten, as in the patch),
   `NEUTRAL_SLACK` (default 0.75). Under LOCAL_BENCH and `NEUTRAL_TRACE=1`, print for every request
   whose final path got shorter through a neutral candidate one line
   `#neutral <r> <u> <before> <witness> <after>` where each path is `paper:depth,...` in output
   paper numbers (use the same out_index mapping as main: paper kCapPaper→0, k<kCapPaper→k+1);
   no `=` characters on these lines.
5. Print the new counters to stderr as `name = number` lines next to the existing `eject_*` ones.
6. Keep the part markers `// ==== ... ====` and the table of contents at the top; add a marker if you
   add a new part (e.g. "Post-processing: two deletions and two repairs (neutral rewrite)").
   Comment the non-obvious code. C++23, must compile with both
   `g++ -std=c++23 -O2 -DCLOCK_SCALE=1.1 -DLOCAL_BENCH` and `clang++ -std=c++23 -O2 -DLOCAL_BENCH`
   (no `<bits/stdc++.h>`).
7. `README.md` (Japanese, short): base = solutions/esw-fixiter, what was ported from PR 114, the
   knobs, the new stderr counters.

## How to run things (strict)

- NEVER run the solution binary on test inputs directly, never run `pahcer run`, and never run
  anything CPU-heavy in parallel yourself: other evaluations share this 24-core machine. Every
  execution on test cases goes through the repo's evaluation script, which takes a global lock:
  `scripts/pahcer_run.py ... --no-record`. Environment variables you set on that command are passed
  to the solution (e.g. `NEUTRAL=0 scripts/pahcer_run.py ...`).
- Fixed designs: run `20261104-224750_esw-fixiter` holds the saved designs of esw-fixiter for all 2000
  seeds. Order-processing-only checks use
  `scripts/pahcer_run.py solutions/neutral-port --design-from 20261104-224750_esw-fixiter --seeds 0-24 --no-record -c "neutral-port check"`
  (keep `--seeds` small, at most 0-100, while developing; the script waits if another evaluation
  holds the lock). Its results are in `/home/sato/ahc074/runs/<run-id>/` (result.json scores,
  out/<seed>.txt, err/<seed>.txt with the stderr; the run-id is printed at the end).
- Equality check: with `NEUTRAL=0`, every `out/<seed>.txt` must equal
  `/home/sato/ahc074/runs/20261104-224750_esw-fixiter/out/<seed>.txt` (seeds 0-24).
- With the defaults: no WA (score 0), `self_wrong = 0`, `op_label_errors = 0`, and report the total
  moves per seed vs `20261104-224750_esw-fixiter` (result.json) and the mean `req_sec`.
- Do not edit anything outside `solutions/neutral-port/`. Do not commit. Do not touch `scripts/`,
  `pahcer/`, other solutions, or `trial_log.md`.

## Report

Write `solutions/neutral-port/REPORT.md` (English or Japanese): what you ported and where (line
ranges), any deviation from the patch and why, the equality check result, the 25-seed (or 100-seed)
total moves vs the base (sum and per-seed log-ratio mean ± SE), req_sec, and any doubt about
correctness. Your final message: a 10-line summary.
