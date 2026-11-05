# Next research for Astra (this session): the structure of the design phase (design-frame)

Thank you for the incompatible-pairs study (merged as PR #130). The user now asks you to research
the design phase as a whole. Their words:

> 現状の設計フェーズは、窓の割当の焼きなまし最適化 → ペア・列配置・ハンドル決定の焼きなまし最適化 →
> フィラーの修正と Hungarian 法 → 穿孔処理、の 4 つの処理を直列に行うという理解です。この枠組みは
> 最適なのでしょうか？ 特に、最初の 2 つの最適化は、独立に行うものなのでしょうか？ 同時最適化する
> わけにはいかないのでしょうか？ あと、cap の位置をいろいろ試すことで、解の多様性につながるかも
> しれないですね。これらの疑問に答え、設計フェーズを高効率化すべく、研究を重ねてもらえますか。

Goal:
- Answer these questions with evidence.
- Find changes to the design phase that give better designs at the same time, or the same designs in
  less time. The time matters: the judge-time model says mean 1.60 s and p99 1.76 s for esw-clean
  (2 s limit).
- Implement and measure them.

## Rules (as before)

- Run test cases only through `scripts/pahcer_run.py` and record the runs (no `--no-record`, except
  for measurement-only builds that exceed the time limit).
- Edit only `solutions/design-frame/` and sibling `solutions/design-frame-*` directories (check
  `ls solutions` first). Base: `solutions/esw-clean/main.cpp`.
- Keep all logs, metrics, switches, profilers, CLOCK_SCALE, LOCAL_BENCH, the DesignStore,
  `@paper` / `@ops`, and the section markers with the table of contents.
- Each solution directory needs a Japanese README.md (first line 改良元: solutions/<base>, then the
  differences and the switches/metrics). No commits; I open the PRs.
- **Division of labor.** The other Astra session works on the internal search of `assign_windows`:
  its proposals, screens and evaluation, with gobj as the objective (solutions/assign-search*). Do
  not duplicate that.
  - Your scope is the pipeline: how the stages are sequenced, coupled, restarted or selected; what
    information flows between them; what objective each stage optimizes for the final design; joint
    moves across stages; the cap.
  - If you need to call `assign_windows` differently (another objective, warm starts, interleaving),
    do it in your own copy.

## The current design phase (esw-clean; local times scaled by CLOCK_SCALE 1.1, means over 2000 seeds)

1. **Window assignment, `assign_windows`: about 0.46 s, 450k annealing iterations + 133k climb steps.**
   - It chooses the 38 generic windows among the 63 active windows (window 63 is the black cap) and,
     for each generic window, its pair of generic sheets (15 choices) and polarity.
   - Objective gobj: the mean cost of 71 vertex-disjoint compatible close pairs, matched greedily.
     - A pair's cost is 0.5 × handle differences + the exact mean generic-layer moves of both targets
       (PosetSums) + 0.04 × differences.
     - Only about 160 of about 3430 close pairs are compatible.
2. **Design annealing (`Design`): about 0.51 s, 14.9M iterations in 4 segments, each restarting
   from the best so far (imp-seg).**
   - Starting from Design::initialize (the same greedy pairing), it anneals the pairs (re-pairing
     among compatible pairs), the column of each unit and the handle order.
   - Objective model_cost = model_col (digs) + model_hole (handle holes, 0.40 each) + model_gc
     (generic moves).
3. **Filler climb (`filler_climb`, 154k iterations, about 0.025 s).**
   - It exchanges two units of the same kind and colors between columns, accepting on
     cur − 0.5 × proxy. proxy is the filler value of the column heads.
   - Then 4 rounds of head-aware reassignment of targets to papers (Hungarian matching, about 0.03 s).
4. **Handle perforation (about 0.015 s).** Then the helper tables (about 0.03 s).

The window assignment is never revisited after stage 1. The design anneal cannot change window roles.

## Measured facts to build on (see trial_log.md, 2026-11-05 sections)

- **Value of more iterations, 2000-seed normal compares (run 20261105-064212):**
  - window assignment 2×: −0.154 ± 0.026%;
  - design annealing 2×: −0.075 ± 0.022%.
- **gobj is causal: about 3% of the score per unit.**
  - The 2× gain matches the regression across random seeds.
  - gobj_after on seeds 0–199: 9.859 / 9.807 / 9.772 / 9.744 at 1× / 2× / 4× / 8×.
- **Design variance (dsel-probe, 8 random design salts × 500 seeds × 8 order sequences).**
  - True design sd: 0.44%.
  - Salting only the assignment: 0.42%. Only the annealing: 0.34%. Only the late stages: 0.05%.
  - Choosing the best of 8 designs by the order sequences: −0.52%. By J = model_cost − 0.75 × proxy
    (r = 0.62 with the true quality, vs 0.44 for model_cost): −0.46%.
  - Two half-length anneals selected by J: −0.04% net (the halving loses about 0.09%).
- **The assignment's greedy matching is nearly optimal.** pair-exact: the exact matching is 0.0017
  lower on average, and using it in Design::initialize changes nothing.

Tried before (trial_log 2026-11-02 to 11-04; do not repeat without a new reason):
- **Restarts and selection of design candidates:** head-restart, sim-select, early-/warm-select,
  head-two-starts (+0.079% on 500 seeds), head-archive, span-select (G = 37–39 built and selected:
  2.8 s), assignment multi-start (+0.13% / +0.31%).
- **Changing windows after the design breaks existing pairs:** map-repair variants lose about 30
  pairs per candidate; map-refine; joint-map, stationary-design (PR 90 study).
- **Time splits between map and anneal:** map60 / map40 both worse; the current split is near the
  optimum.
- **The cap:**
  - as6-cap38 gained −0.199%. A cap turns one handle window into a window that every pair can
    differ on without the comparator.
  - as6-cap38p0 (the cap is output paper 0) gained −0.047%.
  - Searching the cap window during the assignment (as6-capjoint −0.047%, as6-capswap −0.029%)
    added nothing on top of p0.
  - More caps or windows: worse.
- **Design-anneal search improvements (astra-design, 54 candidates):** none beyond 2 SE.

## Questions to answer and directions (yours to choose)

- **Is the serial pipeline a good decomposition?**
  - Quantify the coupling: how much of the final design quality is decided by stage 1, and could a
    stage-1 decision be judged better with stage-2 information?
  - For example: the map's objective counts handle differences uniformly at 0.5, while the anneal
    later puts pairs in columns where some handles are holes anyway. Pair costs in the map could
    reflect what the anneal can do with them.
  - Also: does gobj's greedy pairing match the anneal's final pairs?
- **Joint or alternating optimization.**
  - Can the design anneal include window-role moves (a window's sheet pair or polarity, or a
    generic/handle swap) evaluated on the full model, with repair of broken pairs?
  - Can the map and the anneal alternate, at the same total time?
  - The past failure: changing a window breaks about 30 pairs. Find out whether that holds early in
    the anneal, or for moves restricted to windows used by few pairs.
- **Diversity and the cap.**
  - The cap window is fixed to 63; all windows are statistically alike.
  - Does choosing the cap window per case, or trying several caps or assignments early and
    continuing the best, give a better expected design at equal time?
  - Remember that full restarts lost. Early selection would need a predictor that works early.
- **The later stages.**
  - Are the filler climb / Hungarian / perforation well placed?
  - Could some of them run inside or between anneal segments to steer the anneal?
- **Time.** Where is the design time best spent? Any exact speedup you find in your own copies also
  counts.

## Measure

- **Normal compares (designs change):**
  ```sh
  scripts/pahcer_run.py --compare solutions/esw-clean solutions/design-frame-X --seeds 0-200 -c "..."
  ```
  Then 500, then 2000 seeds with `--extend` when promising. SE is about 0.026% on 2000 seeds.
- **Time:** report the design end time (`helper_end_sec`) and `end_sec` of both arms. Prefer equal
  time; if a change costs time, show its value at equal time (for example against the 2× iteration
  values above).
- Cheap models are fine for exploring. The gobj or model_cost changes of fixed-iteration runs are
  deterministic per seed.

## Report

- `solutions/design-frame/REPORT.md` in Japanese:
  - the answers to the user's questions (pipeline optimality, independence of stages 1–2, joint
    optimization, cap diversity) with numbers and run-ids;
  - what was tried, what worked, and the recommended next steps.
- READMEs for the solution directories.
- Final message: a 10-line summary.
