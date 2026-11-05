# Two new research tasks for Astra (this session): query-memo and cap-ablation

Thank you for assign-search: merged as PR #131 and now the main base. The user asks for two new
studies, in this order. Rules as in task 10:
- record the runs (no `--no-record`);
- run test cases only through `scripts/pahcer_run.py`;
- keep all logs, metrics, switches and profilers;
- one Japanese README per solution directory;
- no commits; I open the PRs;
- touch only your own new directories (check `ls solutions` first).

**Base: `solutions/assign-search/main.cpp`**, the current best. Its designs are saved; use
`--design-from 20261105-115444_assign-search` for request-only comparisons.

The other Astra session works on the structure of the design phase (`solutions/design-frame*`),
including the cap's position or diversity. Do not overlap: your cap task is the ablation only.

## Task A: reuse what was learned when the same target was requested before (query-memo)

The user's words:

> クエリ処理において、過去と同一のクエリが来たときに、過去の処理列の情報を活用する、みたいなことは
> やっているのでしょうか？ やってないのなら、これで改善できるかやってみてほしいです。

Each of the 256 targets is requested about 4 times in 1024 requests (never twice in a row). The
stack changes in between.

1. **Check first.** Does the current request processing keep any information across requests that
   could serve as a memory of past requests for the same target? I believe only the
   within-request caches and the state value exist. Write down what exists.
2. **If nothing like this exists, design and test reuse.** Examples (yours to choose):
   - The previous final move sequence for the same target, adapted to the current stack (re-anchored
     and replayed for legality), offered as an extra plan candidate or neutral-search seed.
   - Per-target statistics from past requests to order or prune the search: which plan options,
     fillers, helpers or rewrites won.
   - Exact reuse when the part of the state that matters for this target is identical to a past
     request (e.g. the same column order and generic order), to save time that the search can spend
     elsewhere.
3. **Measure on fixed designs first.** These are request-only changes:
   ```sh
   scripts/pahcer_run.py --compare solutions/assign-search solutions/query-memo --design-from 20261105-115444_assign-search --seeds 0-200 --orders 2 -c "..."
   ```
   Then 2000 × 2 if promising. Fixed-design runs are not recorded; that is expected.
   - Compare at (nearly) the same req_sec, or show the time saved.
   - Confirm a winner with a normal 2000-seed compare.
   - SE: about 0.003% on fixed designs 2000 × 2, about 0.026% on normal 2000 seeds.

## Task B: is the cap still useful? An ablation (cap-ablation)

The user's words:

> 実は cap って不要になってたりしませんか？ Ablation study をやってみてほしいです。

History (trial_log 「2026-11-02 固定キャップ（[ChatGPT] PR 78）の移植（as6-cap38）…」):
- The cap is a fixed black paper on top of the generic layer. Physical window 63 is its window, and
  it is output paper 0.
- The lifted product paper is put either above it or just below it, which decides window 63's
  color.
- It turned one handle window into a window where any pair may differ without the comparator. It
  costs one paper: 71 pairs instead of 70.
- It was adopted on a much weaker base: as6-cap38 −0.199%, then p0 −0.047%, with G = 38 and 25
  handles. Before it, G = 39 with 26 handles and 70 pairs was the best (as6c2-g39).

Questions: with the current design and request processing, what does the cap contribute now? Would
the solution be better without it?

What to do:
- Build a no-cap version of `solutions/assign-search`.
  - The cap paper becomes a product paper again: 186 product papers, 70 pairs.
  - Window 63 becomes an ordinary window that the window assignment may use (generic or handle).
  - Remove the cap invariants in the request processing where they no longer apply.
- The cap is wired into many places (kCapWindow, kCapPaper, the cap invariants in post-processing and
  helper insertion, the output paper 0). Do it carefully; WA must stay 0.
- Compare with normal compares, since the design changes:
  - G = 38 and G = 39 without the cap, against the current (with the cap);
  - 500 seeds first, then 2000 seeds with `--extend` for the best variant.
- Report the difference ± SE, the effect on the model parts (handle holes, pairs' handle
  differences, generic moves), and the time.
- A clear "the cap still pays X%" is as useful as a removal.

## Report

- `solutions/query-memo/REPORT.md` and `solutions/cap-ablation/REPORT.md` (Japanese), plus the
  READMEs.
- Final message: a 10-line summary covering both tasks.
