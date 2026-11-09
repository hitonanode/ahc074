# Map of the DESIGN side of solutions/dcomp-combo-dual30 (2026-11-09)

Line numbers refer to `solutions/dcomp-combo-dual30/main.cpp` (11,387 lines; `grep -n '// ====' main.cpp` gives the table of contents). Times are means over the 2000 cases of run `20261109-003105_dcomp-combo-dual30` (scaled clock = judge estimate, 24-parallel GCC), computed from `runs/<run>/err/*.txt`.

## 0. Vocabulary (fixed in every case)

- N=64 windows, K=192 papers, P=256 targets. Window 63 is a fixed black **cap** (paper `kCapPaper`=6, bit `kCapBit`); design works on 63 "active" windows.
- **Generic layer**: M=6 sheets (papers 0–5) and G=38 **generic windows** (internal windows 0..G-1). Generic window j compares sheets `edge[j]=(a,b)` with colour `polarity[j]`: a shows that colour, b the other, the rest have holes, so the window shows the colour of the upper sheet (Comparator, l.299–302). 15 sheet pairs; all 15 compared → "complete".
- **Handles**: H = 63−G = 25 handle windows, one per **column** c (`handle[c]`). Column c holds the product papers whose target is served there; a paper in column c is opaque on generic windows and on handles h_0..h_c, holes on deeper handles (`Design::holes`, l.2718).
- **Unit** = one target (single) or a **compatible pair** of targets sharing one paper (holes where the two targets differ; feasible iff the induced relations of the 6 sheets form a DAG, `Comparator::compatible` l.367). U = 191−M = 185 units, `need` = 256−185 = 71 pairs (l.2690).
- gcost(a,b): exact mean generic-layer moves of a pair from a uniform sheet order = `PosetSums::both_of(closure)/1440` (l.10697–10702).

## 1. Pipeline in execution order

Driver: `design_papers` l.10655–10946; called from main l.11200–11216; then helper tables l.11224–11247.

### 1.1 Window assignment (`assign_windows`, l.1335–2620) — ends at `map_end_sec` 0.421 s (p99 0.56)

Purpose: choose which 38 of the 63 active windows are generic, and the sheet pair + polarity of each (`mask[e]`, `pol`). Output: renumbered windows (`permutation`, A rewritten), `comp.edge/polarity`.

Objective **gobj** (l.1342–1345): greedy matching of 71 compatible **close** pairs (Hamming distance ≤ `kCutoff`=26, ~3400 candidate pairs/case, ~165 compatible at a time; pair-exact note trial_log l.716) priced by `0.5·(handle differences) + both targets' mean generic moves + 0.04·(all differences)`; penalty 10 per missing pair; integer keys in 1/3600 (l.1344, 1502). Stable ties by pair index. `gobj_before` 9.876 → `gobj_after` 9.849.

Parts:
- `WindowPairs` l.973, `WindowRelations` l.1013 (packed relations, witness cycles l.1051, AVX2 closure4 l.1072), `evaluate_move` l.1120–1315 (SIMD relation update + cache lookups; GCC uses sparse nonzero lists "sparsebits", Clang the plain scan — alt1 README).
- Constants l.1374–1381: `kCutoff` 26, `kRejectLoss` 3, `kMemoSize` 2^18, `kWindowRate` 0.6, `kMapStall` 256, `kClimbStall` 512, `kTabuAccepted` 4; env `AS_ELITE` (default 1), `AS_WORK` (1.0), `as_screen` fixed 0.
- `matching_cost` l.1477–1555 (radix-sorted keys, branch-free greedy). Move kinds (`as_names` l.2581): window role swap, flip, exchange, **transfer** (l.1814), **cross** (l.1946), **elite** path-relinking toward 8 hashed elite states (l.2163–2307, from assign-search 11-05). Loss screens via bit-sliced counters reject moves that break ≥3 selected pairs before any closure (l.1648–1795, 1916–1995).
- Acceptance l.2455–2497: `temp = 0.05·(0.00125/0.05)^progress`, tabu on reversed move, forced escape to the least-cost cached neighbour after `kMapStall` without acceptance (l.2361–2400, `forced_steps` 735/case). Then **gopt climb** l.2498–2580 from the annealing best (`kClimbStall` 512, `elite_*` stats).
- Iterations: `kMapIters` 450,000 (`MAP_ITERS`), `kGoptSteps` 133,000 (`GOPT_STEPS`), retry 160,000 (l.10649–10650). Fixed counts, no clock (final-time-pace replaces them by deadlines).
- Retry loop l.10677–10711: if `Design::initialize` fails, G → 32, then 28, then emergency. In the 2000 cases G=38 always (`G` stat = 38 everywhere), so retries and `emergency_design` (l.9447) are dead paths in practice.
- Time share (Task 13, SHARES13): window search 31.9 %, gopt 8.0 % of the design; profile (Task 8): relation updates ~48 %, matching ~23 %, screens ~23 %.

### 1.2 Initial design (`Design::initialize`, l.2794–2910) — inside map_end, a few ms

Pairs: greedy over compatible pairs priced `0.65·handle diffs + 2·gcost + 0.04·diffs` (l.2809; note the different weights from gobj), completed by length-3 augmenting paths (l.2819). Columns: both colours in every column (singles first, l.2855), sizes ∝ c+1.5 (l.~2882), filled from the deepest column, pairs first. Returns false if no 71 pairs or a one-colour column.

### 1.3 Design annealing (`Design::anneal` l.2917, `Annealer<NR>` l.2948–3534) — `dv_anneal_sec` 0.394 s

Objective `cur` = Σ_c `colcost(c)` + Σ_j `hcost(j)` + Σ_units `gc(u)` (l.2722–2755):
- `colcost` = least weighted dig depth of a column (pairs on top; +(np−1) when all pairs share one handle colour; +1e5 if a handle colour is missing) — l.2727–2737. Mean 2.96 moves/order.
- `hcost(j)` = `4·kHoleWeight·(x·y + 0.5·reset·min(x,y))/(x+y+reset)`, x,y = holes of colour 0/1 at handle j, `reset = reset_strength·nt[c]` = 2·targets of the column (refreshed each segment, l.2751); `kHoleWeight` 0.38 (l.2674), `reset_strength` 2.0 (l.2686). Mean 3.94.
- `gc(u)` = 2·gcost for a pair, 0 for a single. Mean 1.36. `model_cost` total 8.26 vs real 10.02 moves/order (fillers are not modelled — deliberately, see §4).
- Head probability used downstream: `head_probability` l.2745.

Schedule: `kAnnealSegments`=4 (l.2916); per segment `refresh_reset` and `temp = 2.0·(0.015/2)^progress`, times `anneal_reheat^((1−progress)/(1−reheat_start))` (l.3422–3423). Acceptance `d ≤ 0 || d < temp·(−log U)` (l.3096). Move mix per mille (l.3405): handle swap 150, column swap 20 (distance 1..4), pair replace 100 (3-unit rotation, l.3437), target exchange until 430, column exchange until 750, unit move until 900, two-unit moves rest. AVX2 column/hole evaluation (`Annealer<4>` if H≤32).

Budget `kAnnealIters` 11,175,000 (`ANNEAL_ITERS`; from time-alloc 11-05, 0.75× of 14.9M): shared prefix = segments 0–1 = 5.59M iters (l.10896), then 4 branches each `anneal_iters·branch_scale(0.25)` over segments 2–3 = 2.79M… but divided by 4 segments → 1.397M per branch (l.10921; `anneal_iters` stat 11.177M total confirms). Branch i>0: rng salted, `anneal_reheat`=2 (branch 0: 1), `reheat_start`=0.5. Time share: shared seg0 11.4 %, seg1 9.0 %, 4 branches 16.1 %.

### 1.4 Finishing of each candidate (`finish` lambda, l.10716–10888) — `dv_finish_sec` 0.184 s for 9 candidates

For `extra`=0 (branches 0–3) and 1 (cold refinish; ids 4, 6):
1. **Filler climb** `filler_climb` l.3583–3734: random exchanges of the columns of two pairs (or two singles) that keep their handle colours; accept if `Δcur − kClimbProxyWeight·Δproxy < 0` (l.3709), `kClimbProxyWeight` = 0.5 (l.2675, set at l.10903; chosen 11-05, trial_log l.496: λ 1.0→0.5 gave −0.072 %). `proxy` = Σ over column heads of `filler_gain` (l.3557–3576: expected handle fixes saved minus 1 placement − 0.6 return), heads = strongest eligible unit per column/colour weighted by head colour probability; head probabilities frozen during the climb; gain cache (dcomp-climb-cache, −19 ms). 50,000 iterations (branches) / 25,000 (cold refinish); `climb_env` hard-coded 50000 (l.10666). Chosen candidates: 23 accepts, proxy 0.577→0.585.
2. **Head-aware rematch** `rematch_probability(d, 2 or 1, weight 1.0, strength 2.0)` l.4027–4189: `ProbabilityHead` l.3822 (filler value of heads, gradient l.3902), Hungarian l.3743 (AVX2), each pair keeps a random anchor, cost = linearised hole gradients + head filler value, cycles tried in predicted-gain order, accepted only on exact decrease of `cur − weight·filler`. Chosen: 67 units changed, 1.42 iterations, 5.2 ms.
3. Papers printed l.10740–10788: order = 6 sheets, cap, columns 0..H−1; within a column colours alternate starting with the handle-demand majority colour, by weight (l.10750–10769). `ded[t]` = paper of target t.
4. **Perforation** `Perforation<25>` l.9510–9984, `run(0.7)` (l.10822): one random pass over (head paper, shallower handle) candidates; a hole is kept when `Δhole_cost − 0.7·Δprofit < 0`, profit = interval DP over `kSamples`=8 head-colour samples (l.9513, 9675), owner bias correction (`last_owner_corrected`, argon condbound), screen `separate_profit` (l.9603). Result: 7.6 holes, 4.6 accepts of 463 trials, 6.3 ms; `perf_donor_gain` 0.012, owner 0.0035 moves/order (tiny).
5. **Perforation-aware reassignment** l.10840–10886: `rematch_probability(d, ARGON_D2_LATE_ITERS=1, weight 1.25, strength 2.0, &extra holes, extra_mode 4)` — Hungarian once more with the extra holes fixed to slots, singles' handle colours free (flex125), rejecting cycles that empty a colour (l.4155). 23 units changed, model −0.0033, 4.4 ms.

For `extra`=2 (**warm** refinish, ids 5, 7, 8): skip climb and pre-rematch; start the perforation from the holes of the current best state (`warm_state`, l.10806–10813, `perforation.allowed = natural_opacity`), then late rematch.

Per-candidate costs (Task 8 profile, before climb cache): branch climb 13.5 / pre-rematch 9.5 / perforation 6.8 / late rematch 5.1 ms; cold 7.5/4.8/7.0/5.4; warm 0/0/6.6/5.7.

### 1.5 Candidate construction and selection by V (l.10889–10945) — `dv_eval_sec` 0.023 s

9 candidates: ids 0–3 = the 4 branches finished (`complete(i,0)`); ids 4..8 = 5 repeats from `best_assignment` (the Design of the current best V) with salt `repeat`=1,1,2,2,3: j=0 cold, j=1 warm, j=2 cold, j=3 warm, j=4 warm (l.10927–10936). Every candidate gets `V = value.from_design(candidate)`; the min wins (`dv_chosen`). Then `improve_initial_columns` on the winner only. `chosen_log` replays the winner's stderr.

Observed: `dv_chosen` median 7, mean 5.9; only 582/2000 winners had climb lines (ids 0–4, 6), so **~71 % of the time a warm refinish (5, 7, 8) wins** (ordered8 note: 62.5 %). `dv_first` 10.086 → `dv_best` 10.047 (V's own scale, ≈ −0.39 %).

### 1.6 Initial column order (`improve_initial_columns`, l.10036–10081) — 0.5 ms
Per column, a small DP over the two colour groups (sorted by `adaptive_weights` = frequency + filler demand) minimising expected dig depth + depth to the first paper of each colour × hole demand; permutes paper numbers and `ded` only. 115 of 185 papers move; `initial_order_model_gain` 0.13. Applied after V (V never sees it).

### 1.7 Helper tables and request-side tables (main l.11224–11247) — anneal_end 1.024 → helper_end 1.044 s
`init_adaptive`, `comparator.build_tables` (720 orders), `Interleave::init` (l.4204–4293: for each target, papers of other columns that can sit inside the generic layer and show its generic holes; `helper_papers` 3431/case; time limit 1e300 — never gives up), `init_lookahead`, Column MDP tables (`ColumnMdp` l.4305; `colmdp_sec` 9.8 ms; limits `COLMDP_MAXLEN` 14 papers, 40000 full states; `colmdp_columns` 24.9/25 — the deepest column (~14 papers from sizes ∝ c+1.5) sits at the limit).

### 1.8 Totals
map 0.421 + anneal 0.394 + finish 0.184 + V 0.023 + helpers 0.020 ≈ helper_end 1.044 s (p99 1.206). Requests 0.499 s; end_sec 1.558 (p99 1.742, max 1.810). Task 13 shares used by the final version: window 31.9 %, gopt 8.0 %, shared anneal 20.4 %, branches 16.1 %, rest 23.6 %.

## 2. V (`namespace deval`, l.10082–10640)

Design-only surrogate of moves/order; no stack or request stream (l.10083–10084).
- `State` l.10093: targets, papers (opaque/black by handle index `op/bl`), `freq`, per-column `nc, nt, n1, p1`, per-handle hole counts `xy[c][colour]`; `probabilities(strength)` l.10128 = head-colour probability with reset `strength·nt[c]` (same formula as the annealer).
- `Donors` l.10139 (head papers as fillers), `expectation` l.~10190–10280: per target, an interval DP choosing fillers vs digs over Sobol quadrature points of head colours (`samples_for(H)` l.10306; bases for H = 25/31/35; 16 points by default), fixed design-independent points; exact mismatch control variates (header comment l.9).
- `GenericTable` l.10330: exact generic costs (direction-specific `PosetSums` sum, l.762).
- `static_features` l.10350–10420: `col`, `gc`, `holes`, `extra_holes`, moments (p1..p3) of 8 per-target quantities, head-hole features for 6 reset strengths {0, .5, 1, 2, 4, 8} × depth powers d0–d3, last1/2/3/5 bands, balance; column-statistic moments.
- `add_stationary_features` l.10437: 2-step mean-field update of head probabilities with the DP's flip rates, cover summaries `f_s2_*`, `m_s2_it1/2_*` (cost, fix, fill, fdig, covered, length, lastfix, tailfix).
- `kIntercept` 2.659, 142 linear terms `kTerms` l.10467–10609 (largest: col 0.519, gc 0.266; `G`, `H` 0). `DesignValue::operator()` l.10616; adapter `from_design` l.10625.
- Fit: ridge/linear on 7 designs × 8 order lists per seed, seeds 0–499 of SOTA argon-des-perf-latew105 (deval-seed, trial_log l.1359–1380). Validation seeds 500–999: within-case correlation 0.81 (noise-corrected 0.91) vs model_cost 0.36; selecting among 7 designs gives −0.543 %. Among 4 branches V captures ~85 % of the oracle gain (l.~1400). V3 = 0.93 col + 1.03 gc + 0.88 m_s2_it2_cost has r 0.798 and nearly the same selection gain (deval-vanalysis); 87 % of the within-case variance comes from the 10 DP2 features. Evaluation 2.5 ms (16 points; 8/4 points lose 0.006/0.02 % of selection gain). Refitting on branch candidates did not help (l.1444). V was **not refit** after the flex125 rematch, warm refinish, ordered8 and perforation changes.

## 3. Hand-off to the request side

`DesignState` l.9991–10002: `M, G, H, permutation, A` (with cap bit), `edge, polarity`, `papers` (K `Paper{opaque, black}`, after perforation), `columns` (−1 for sheets/cap), `ded` (paper per target), `handle` (window of h_c). `make_solver` l.10005–10030 derives everything else: `h_opq/h_blk` (handle bits per paper), `gmask/hmask`, initial order = identity with the cap rotated to the top (the first legal move). Under LOCAL_BENCH `DesignStore` l.10958 saves/loads exactly these fields (`--save-design`/`--design-from`).

Design assumptions the request side relies on:
- Paper layout: 0..5 generic sheets, 6 cap, then columns contiguous in increasing depth with the within-column initial order from §1.6; `col_of[k]`, each column paper opaque on all generic windows and on h_0..h_c (minus pair differences and perforation holes) — the solver's dig/handle-fix model (`Solver` l.4566+, future-cost l.4761) and Column MDP typing (2·paired + handle colour, l.4296) depend on this.
- Complete comparator with M = `Interleave::GM` = 6 is required for helpers and the look-ahead (l.11235); PosetSums requires M=6.
- A pair's two targets differ only at holes; each target has exactly one `ded` paper; heads per column/colour exist (both colours in every column).
- Column MDP covers columns ≤ 14 papers; a deeper-column design would silently lose MDP values.
- Request-side time: 0.5 s; design changes that change `req_sec` (e.g. more helper papers) must be paid from the design budget in the final version.

## 4. History per stage (what is closed)

**Window assignment.** The largest lever: 2× iterations −0.154 % (+0.6 s), 8× ≈ −0.35 % (gobj ≈ 3 %/unit, trial_log l.575–604, runs 20261105-064212/065425). gobj is causal (direct optimisation keeps its gain). Done: assign-search elite paths + loss screens (−0.054 %, 20261105-113833), design-fast/packed speedups (argon-des-design-packed), ordered8 gather closures, Task 9 sparsebits (−20.7 ms, GCC only). Closed: pool evaluation (map-pool, worse gobj), exact matching instead of greedy (gobj gap 0.0017, ~0.005 %, l.716), reranking by newly valid pairs / selected-pair cost, 2-exchange cycle repair, sparse exact evaluation (1.74× slower), tabu-stall release (dcomp-unstall +0.0002 %), map 470k (+0.028 %), two half-budget maps (+0.182 %, 20261108-104942), G=37 flat but 0.09 s slower, G=39 +0.097 % (l.811), ordercost/orderfast/balanced objectives (l.788), cap window choice (l.788, l.1338), revisiting comparator pairs after the fact (argon D1: 6/200 changed, no effect, l.926). Incompatible pairs (incompat-pairs l.728, ch5-access l.1661, nogen line): closed — need <0.5 moves per fix, measured 2.9–3.8.

**Design annealing.** 2× iterations −0.075 % (+0.55 s); 0.75× costs +0.049 %, 0.6× +0.105 % (time-alloc, l.831); cheapest stage to cut. Branching: 4 branches on the second half with reheat 2 (deval-vbranch-o3 −0.165 %, l.1380s); independent quarter anneals −0.128 %, last-segment branching −0.114 %, 12 candidates −0.237 % at 1.6 s; two independent half-length anneals +0.042 % (20261108-104718); successive halving by raw V +0.002 %. Objective changes closed: V-like per-iteration handle terms (deval-vanneal/vsingle/vtarget2, no effect), deepest-handle weights 1.5–3 (lastw +0.04..+0.11 %), V3 pre-climb (+0.116 %, finishing undoes it), mixing V's local term (+0.061 %), Hungarian mid-anneal (+0.054 %), exact initial pairs (PAIR_EXACT_INIT, flat). Lesson (l.1420–1440): the anneal is meant to ignore fillers; finishing optimises them.

**Filler climb / rematch.** λ 0.5 (−0.072 %; 0.4/0.6 flat; λ 0 worse even with 4× iterations, l.496); climb 4× +0.12 s not worth it; cuts of climb/rematch not worth it (time-alloc). Rematch: weight 1.0 → 1.05 (−0.012 %) → 1.25 with free single colours (flex125, −0.094 % with request changes); weight 0.7/0.85 worse (+0.087/+0.038 %); 2 or 4 late iterations +0.003 % and +13/+26 ms; 5 pre-perforation iterations +0.0002 %; moving whole targets between columns +0.037 % (prediction wrong: overlapping-interval proxy overcounts ~76 %, l.1111–1118); climb-before-Hungarian order reversed +0.139 % (postclimb). Output-identical: climb cache (−19 ms, adopted), rematch polynomial memo (+7.6 ms, rejected), lazy Hungarian (−4.4 ms, adopted 11-05).

**Perforation.** perforated-eight (−0.059 %, 11-04), owner-bias correction + bound (condbound −0.008 %, holes 4.3→3.5), gain cache, strata cut; samples 32→8 flat; 2nd/3rd head papers, 2-hole moves, exposure rates: no effect (91–96 % of apparent gain was owner-side sample bias); acceptance weights 0.75/0.80 flat; re-perforating after the late rematch −0.0138 % at +17 ms (unadopted, l.1111); restoring unneeded extra holes −0.001 %. Present weight 0.7 fixed since 11-05.

**Candidates / V.** seven-wide (3 refinishes, −0.059 %), ordered8 (4 refinishes, 2 warm, + initial order, −0.064 %), 9th candidate (dcomp-nine −0.0145 %, 20261108-114412), 10th (−0.0045 % more, over time; −0.003 % in Task 11). V refinement of a finished design (v3refine +0.04 %: designs are locally optimal under finishing). Warm refinish chosen 62–71 % of the time.

**LNS (Task 7, lns-notes).** Destroy-and-repair of windows/pairs/columns at 2×/4×/8× budget loses to full redesign by +0.19/+0.26/+0.37 %; full redesign at 2/4/8× gives −0.25/−0.42/−0.60 %. Closed.

**Time-based design (Task 13).** Deadline version at 1.05 s +0.044 ± 0.026 %, at 1.22 s −0.006 ± 0.026 % (20261108-234310/234311). Final version uses 1.22 s.

## 5. Open questions and stale spots

1. **Dead/stale constants.** `kClimbIters` and `kMatchIterations` (l.10651) are never used: `climb_env` is hard-coded 50000 (l.10666), so `ITER_SCALE` does not scale the climb despite the comment (l.10645); warm candidates ignore it anyway. `kMapRetryIters` and G retries never fire (G=38 in 2000/2000).
2. **Three different filler weights**: climb 0.5 (`kClimbProxyWeight`), pre-rematch 1.0, late rematch 1.25, perforation 0.7. Each was tuned alone at a different point of the pipeline; no joint sweep recorded after flex125/ordered8/nine.
3. **Pair pricing differs**: gobj uses 0.5·hd + gcost + 0.04·d (l.1343), `Design::initialize` 0.65·hd + 2·gcost + 0.04·d (l.2809). Only the initial pairs were probed (exact matching: flat). The 71-pair count (`need`) and cutoff 26 are fixed by M and G; 87 % of gobj pairs survive to the final design (design-frame, l.773).
4. **Hole cost model**: `kHoleWeight` 0.38 and `reset_strength` 2.0 date from the 11-0x regression (trial_log l.184: ≈0.38 per hole, flat in depth); V's DP finds real per-mismatch cost 0.79 (shallow) to 0.96 (deepest) vs the anneal's flat 0.76 (l.~1415), yet reweighting the deepest handles hurt. The reset term (`2·nt`) in `hcost`, `head_probability`, `filler_climb` (l.3598), `rematch` (strength 2.0) and V (`probabilities(2.)`) is one shared constant without a recorded sweep since the V study.
5. **Annealing internals never swept in the log**: move mix (150/20/100/430/750/900 ‰, l.3405), `kColSwapDist` 4, `kAnnealSegments` 4, temperature 2.0→0.015, reheat 2 and `reheat_start` 0.5 (only 2 vs 4 tested: 2 better), branch 0 without reheat.
6. **Window anneal internals never swept**: temperature 0.05→0.00125, `kRejectLoss` 3, `kWindowRate` 0.6, `kMapStall` 256 / `kClimbStall` 512, elite pool of 8, `AS_WORK`.
7. **V is stale relative to the pipeline**: fit on 11-07 SOTA designs before flex125 (free single colours), warm refinish, 9 candidates and the initial column order (applied after selection, invisible to V); the Column MDP and helpers are not in V. Candidates differ mostly by finishing (within-branch true SD 0.026 moves/order vs 0.040 for independent anneals, 0.049 for full redesign), so V selects among near-duplicates: 5 of the 9 candidates share one assignment.
8. **Candidate schedule**: ids 4–8 all restart from the best-so-far; cold repeats (4, 6) are chosen rarely (582 cases include ids 0–3 too). Whether 2 cold refinishes (≈25 ms) are better spent as another warm one or as map/anneal iterations is untested after dcomp-nine; a 10th candidate gave −0.003..−0.0045 %.
9. **Within-column initial order DP** (§1.6) uses frequency + filler demand but not the Column MDP; its `initial_order_model_gain` 0.13 is a model unit never validated against replays beyond ordered8's bundle.
10. **Column size profile ∝ c+1.5** (l.~2882) and H=25 are fixed since early versions; the deepest column (~14 papers) touches `COLMDP_MAXLEN` 14 — a design with a 15-paper column would lose MDP values silently (`colmdp_columns` 24.9/25 shows it already happens in some cases).
11. **Perforation reach**: only one head per column/colour and only shallower handles; gains are tiny (donor 0.012 moves/order) but the stage costs 6 ms × 9 candidates ≈ 55 ms of design time — the time/benefit of running perforation on all 9 candidates (vs only on the V-best few) is unrecorded.
12. **Helper tables** (`Interleave::init`, limit 1e300) and Column MDP are built once after selection; no experiment on building them for V (they are what the request side actually uses).