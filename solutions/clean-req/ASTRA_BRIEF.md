# Task for Astra: clean up the current best solution (two parts, two sessions)

The user asks (after the time-budget re-balancing, which is finished):

> 現状 best の解法のコードの整理をしてもらえますか。ちょっと長すぎて agent が読むのもたぶん一苦労なので...。
> 例えば以下をやってほしいです。
> * スコアに効いていない工夫は削除する（ablation study はちゃんとやる）
> * 実現したい機能に対して、現状のコードはとりあえず動いてはいるが、最適な書き方でなかったり、もっと整理して
>   書くことでコードの見通しがよくなったり、似た機能のコードが二か所にあったり、といった問題がある箇所を
>   特定し、整理する
> * もし冗長なコメントがあれば削除する
> ただ、後続の agent が整理後のコードをもとにさらに改善を行うので、その際に困るような修正（必要なログ出力とか
> プロファイラのコードとかコメントまで取っちゃうなど）はしないでください。

**Base: `solutions/time-alloc/main.cpp`** (9455 lines). It is the current best, with the tuned time
budget. Two Astra sessions split the file by region (below). I (Claude) merge both results into one
solution, so stay strictly inside your region.

## Rules

- Run test cases only through `scripts/pahcer_run.py`. Record normal runs (no `--no-record`);
  fixed-design runs are never recorded.
- Work only in your directory (below). No commits. Do not touch `scripts/`, `pahcer/`,
  `trial_log.md`, or other solutions.
- **Environment variables reach every solution in a `--compare`.** For ablations, use private
  switch names, or hard-coded copies in your own sibling directories (`solutions/clean-req-*`; check
  `ls solutions` first).

## What to do in your region

1. **Ablate features whose contribution is unclear, then remove the ones that do not pay.**
   - Candidates: heuristics, extra candidate generators, special cases, secondary passes, unusual
     terms.
   - Request-side features: measure on fixed designs,
     `--design-from 20261105-141234_time-alloc --orders 2`, 200 seeds then 2000 seeds. SE is about 0.003% at
     2000 × 2.
   - Design-side features: normal compares, 500 then 2000 seeds (SE about 0.026%), and the
     deterministic model metrics (gobj_after, model_cost and its parts) as a sharper guide.
   - Remove a feature when:
     - its measured contribution is negligible (fixed designs: within +0.003%; normal compares: not
       worse by more than 1 SE and model metrics not worse), or it costs more time than it gains; and
     - removing it simplifies the code.
   - Keep a feature that pays, even if complex. Record every ablation (feature, difference ± SE,
     time, decision).
2. **Refactor without changing behavior.**
   - Targets: duplicated logic (similar code in two places), awkward control flow, dead variables and
     parameters, functions that can be merged or simplified, and comments that repeat the code or
     describe history ("esw-ptune: 0.6 -> 0.7").
   - Verify byte-identical stdout, and all non-timing stderr lines, against the base on the same seeds:
     normal 200 seeds, plus fixed designs 200 × 2 for request code.
3. **Keep what later agents need:**
   - the stderr `name = value` metrics, the `@paper` / `@ops` labels and output, the heavy traces;
   - the profilers (COLFAST_PROFILE, AF_PROFILE, F3_PROFILE, DESIGN_PROFILE, POSET_VERIFY …);
   - the budget switches (iteration counts, F3_* search budgets) that control features which stay;
   - CLOCK_SCALE, LOCAL_BENCH, the DesignStore, the emergency design;
   - the section markers with the table of contents;
   - the comments that explain what a part does, its invariants, and why a non-obvious choice was made.

   Switches that only select an alternative already measured as worse may go with that code path.
   Mention them in your report.

## Final checks of your part

- **Your final file must be the base with only your region changed**, so that the two parts merge.
  If you need to change anything outside your region (a shared helper, a constant), do not; list it
  in your report instead.
- **Combined effect of all your removals vs the base:**
  - normal 2000 seeds: not worse by more than 1 SE;
  - for request code, also fixed designs 2000 × 2: not worse by more than 0.005%;
  - `req_sec` / the design end time not larger.
- GCC and Clang builds (`-std=c++23 -O2 -Wall -Wextra`, with and without `-DLOCAL_BENCH`) without new
  warnings.
- Report:
  - your region's line count before → after;
  - `solutions/clean-req/REPORT.md` in Japanese, listing every ablation and every refactoring with its
    verification run-id;
  - the README (first line 改良元: solutions/time-alloc);
  - final message: a 10-line summary.

## Your region: the request processing (you are Astra 1; directory `solutions/clean-req`)

The sections (by their `// ==== <name> ====` markers in time-alloc):
- Request profiling (COLFAST_PROFILE): inclusive and exclusive times;
- Analysis output (LOCAL_BENCH): move labels;
- Column MDP: long-run values of the order of a column;
- all "Solver: …" sections;
- all "Request plans: …" sections;
- all "Post-processing: …" sections;
- Solver: previous-query plans;
- Request processing (process);
- main: requests;
- main: statistics.

Do not edit:
- the other sections;
- the header comment with the table of contents (I update it at the merge; list any section you add,
  merge, rename or remove);
- the Common section.

Do not change the interface used across regions:
- the Comparator and PosetSums types used by the Solver;
- Interleave (the helper tables) as used by the request plans;
- DesignState / make_solver;
- the Solver members that the design code calls (e.g. handle_bits, used by the perforation).

Report any such need instead.

Request-side ablations should use fixed designs (`--design-from 20261105-141234_time-alloc --orders 2`).
Good candidates are the many SearchConfig features and the post-processing passes. In your earlier
profile, the eject + re-edit passes cost 73 ms per case for little objective gain, and the neutral
re-edits 45 ms. Measure; do not assume.
