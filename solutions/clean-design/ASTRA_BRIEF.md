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
  switch names, or hard-coded copies in your own sibling directories (`solutions/clean-design-*`; check
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
  - `solutions/clean-design/REPORT.md` in Japanese, listing every ablation and every refactoring with its
    verification run-id;
  - the README (first line 改良元: solutions/time-alloc);
  - final message: a 10-line summary.

## Your region: the design phase (you are Astra 2; directory `solutions/clean-design`)

The sections (by their `// ==== <name> ====` markers in time-alloc):
- both "Generic layer: …" sections;
- both "Window assignment: …" sections;
- Design: units, columns and the cost model;
- Design annealing;
- Filler climb;
- Head-aware reassignment (Hungarian);
- Helper tables (Interleave);
- Emergency design;
- Handle perforation;
- Design state (DesignState, make_solver);
- Design iteration counts;
- all "design_papers: …" sections;
- Saving and loading the design state (DesignStore);
- Analysis output (LOCAL_BENCH): paper attributes;
- main: input, main: the design, main: helper tables and the generic look-ahead, main: simulation
  harness, main: output of the papers.

Do not edit:
- the other sections;
- the header comment with the table of contents (I update it at the merge; list any section you add,
  merge, rename or remove);
- the Common section.

Do not change the interface used across regions:
- the Comparator and PosetSums types used by the Solver;
- Interleave as used by the request plans;
- DesignState / make_solver;
- calls into Solver members (e.g. handle_bits in the perforation).

Report any such need instead.

Design-side ablations need normal compares, since the design changes. Use the deterministic model
metrics as a sharper guide: gobj_after, model_cost and its parts, proxy_after. Candidates include
special cases, secondary moves and heuristics in assign_windows (screens, escape, tabu, cross moves),
the design annealing moves, the filler climb, the reassignment and the perforation. Remember that the
window assignment's search is valuable (its iteration count pays). Prefer removing parts that do
not pay over weakening the search.
