# Research brief for Astra: using incompatible pairs (incompat-pairs)

You are a new Codex session. Another Astra session works in parallel on the window-assignment search
(solutions/assign-search*); do not touch its directories.

Read first:
- `CLAUDE.md` (project rules, in Japanese);
- `docs/statement_ja.md` (the problem);
- the sections of `trial_log.md` cited below.

## Rules

- Run test cases only through `scripts/pahcer_run.py`. It serializes evaluations with a lock;
  another agent also evaluates, so expect waits. Never run the solution or the tester directly on
  many cases, and never run anything CPU-heavy in parallel with evaluations.
- **Record your runs (no `--no-record`)**, so that the user sees them in `pahcer list`. The exception
  is a measurement-only build that exceeds the time limit: it would set per-case best scores the real
  solution cannot reach.
- Fixed-design comparisons (`--design-from`, `--orders N`) are never recorded; that is fine.
- Edit only inside directories you create: `solutions/incompat-pairs/` and sibling
  `solutions/incompat-*` directories (check `ls solutions` for name clashes first).
- Each solution directory needs a Japanese README.md:
  - first line: 改良元: solutions/<base>;
  - then the differences, switches and stderr metrics.
- No commits; I commit and open the PRs. No edits to `scripts/`, `pahcer/`, `trial_log.md` or other
  solutions.
- The base for any implementation is `solutions/esw-clean/main.cpp` (the current best). Keep its
  CLOCK_SCALE, LOCAL_BENCH, DesignStore, `@paper` / `@ops` output, stderr metrics, experiment switches,
  profilers, and the section markers with their table of contents. The user wants logs kept.

## The question

In the current design, two targets u, v share one product paper (71 such pairs; 114 targets get
their own paper) only if their pair is **compatible** with the generic layer.

**How the generic layer shows colors.**
- 38 generic windows each compare two of the 6 generic sheets. At such a window, sheet a shows one
  color, sheet b the other, and the window shows the upper one.
- On the generic windows where u and v differ, the shared paper has holes. There the generic layer
  must show u's colors for u and v's for v.
- Each differing window therefore requires an order of its two sheets for u (and the reverse for v).
  The pair is compatible iff these requirements form an acyclic relation, with no opposite
  requirements on one sheet pair.

**What the constraint costs.**
- Only about 160 of the about 3430 close pairs (distance ≤ 26) are compatible. This forces worse
  pairs, with more handle differences.
- Ignoring compatibility would cut the moves by about 5.3% (cons-probe). The model estimate is
  −0.557 moves/request at the same generic cost per target, and about −2.4% at 3.0 generic moves per
  target (compat-price).
- That is the size of the gap to the top competitor.

**The user's intuition.** The request processing has become very flexible since those attempts. It
now has:
- neutral rewrites of the moves;
- a column-MDP state value;
- helper papers inserted into the generic layer;
- filler chains;
- post-processing that can delete, re-anchor and repair moves.

With that machinery, an incompatible pair might be displayable cheaply enough.

**Your task:**
1. Find a mechanism, design plus request processing, that lets the design use incompatible (or
   "almost compatible") close pairs at a total cost below their benefit.
2. Quantify it.
3. If promising, implement and measure it.

## What was tried and failed (read these sections of trial_log.md)

- 「2026-10-31 対の整合の制約の値段と、汎用層の向きの費用（cons-）」
  - Ignoring compatibility: −5.31%.
  - The best incompatible partners have about 3.2 incompatible blocks per pair, so "parts that fix a
    few windows cannot rescue them".
  - A paper is worth about 0.45–0.55% of the score: two spare dedicated papers cost +1.08%.
- 「2026-11-02 手の内訳の分析…（compat-price）…（astra-struct）」
  - compat-price numbers.
  - astra-struct found no structure saving ≥ 0.3 moves/request.
  - The cap paper (キャップ紙) idea.
- 「2026-11-03〜04 PR 90 の構造の変更…（不採用）」, the paragraph starting 補助紙・補修紙で整合しない対を共有する:
  - weave-lab: helper papers can newly display about 33 of the incompatible close pairs per case. But
    the helper is usually tied to one paper, and taking it out, placing it and returning it costs
    about 4.6 moves per request.
  - About 20 variants, all worse or flat: patch-code, overpatch, access-code, handle-patch,
    filler-code, head-weave, front-helpers, helper-garden, hole-helpers, alternate-carrier,
    cover-code, cap-patch, overcoat-code, sparse-coat, mixed-front, virtual-column, anchor-code.
  - free-code displays all 71 pairs at +1.04 to +1.32 moves per pair.
  - Conclusion recorded: "表示できる対は作れるが、安く使える対を数十組同時に作れない" (one can make some
    incompatible pairs displayable, but not dozens of them cheaply at the same time).
  - Also "1 枚の紙で 3 目標を共有する": impossible with the comparator.
- PR 115 (a ChatGPT report): a two-window cap was +0.10% worse. Relaxing the DAG constraint of
  product pairs with existing helper papers was analyzed but not shown to win.
- The ChatGPT draft PRs 56 / 57 (as summarized in trial_log 2026-11-02, the astra-anneal line):
  - 3 windows as a 4-way gate: +0.4 to +0.5%.
  - Rescuing incompatible pairs with 2 helper papers: +0.07 to +0.62%.

So naive "fix the cycle with a helper" mechanisms lose. The economics are the crux:
- An incompatible pair must save more handle holes (and pair cost) than the extra moves it causes
  each time one of its two targets is requested (1 request in 128 per pair).
- It must not consume scarce resources: papers, generic-layer slack.

## Directions to consider (yours to choose; justify with numbers before implementing)

- **Dynamic displays.** For an incompatible pair's request, a cycle means no single order of the 6
  sheets shows all differing generic windows right. Can the request processing show the target by
  combining the generic layer with something it already moves anyway?
  - Examples: the requested paper itself placed between generic sheets; one generic sheet lifted
    above the product paper for that request; the previous request's paper as a temporary cover;
    a filler at a generic window.
  - What is the exact extra move count per request, and how often can it be combined with moves that
    are made anyway?
- **Near-compatible pairs.** Pairs with exactly one conflicting window, or one cycle broken by one
  window. How many are there, and what would they save over the current matching?
- **Design-side accounting.** The map (assign_windows) and the design annealing would need a cost
  for using such pairs, so that they are used only when they pay.
- Anything else you find, including a proof that the economics cannot work: a solid negative
  result with numbers is also valuable.

## Measurement

- Prefer cheap exact models or simulations first: for example the potential saving per pair class,
  and the extra moves per request of a mechanism.
- Then prototypes evaluated with `scripts/pahcer_run.py --compare solutions/esw-clean solutions/incompat-... --seeds 0-200 -c "..."`.
  - If clearly negative (better), extend to 2000 seeds with `--extend`.
  - The SE on 2000 seeds is about 0.026%.
- Report each idea with its numbers and run-ids.

## Report

- `solutions/incompat-pairs/REPORT.md` (Japanese preferred), plus READMEs for any solution
  directories.
- Final message: a 10-line summary of what works or why it cannot.
