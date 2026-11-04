# Task 9, revised scope (from the user): keep the logs and the analysis facilities

The user has changed the scope of the refactoring: **do not remove logs and the like, because they
are needed for future improvements.** Your run was stopped for this. Start again from
`solutions/esw-speed/main.cpp` (overwrite your current `solutions/esw-clean/main.cpp`, which removed
some of these). Keep your helper scripts only if they help, and delete them at the end. Everything
else in the first brief (`ASTRA_BRIEF.md`) still holds, especially:
- byte-identical output;
- the verification on 2000 seeds plus the fixed designs;
- C++23 with g++/clang++.

## Keep, unchanged in behavior and output

- **Every stderr line the program prints today.** All `name = value` metrics, under LOCAL_BENCH or
  not, and their names; the `@paper` / `@ops` analysis output; the heavy traces (`heavy_log`,
  `#heavy` / `#heavycand`, the trace/predict paths).
- **Every profiling switch:** COLFAST_PROFILE (CF_SCOPE / cf_report), AF_PROFILE, F3_PROFILE,
  DESIGN_PROFILE, POSET_VERIFY, and any other.
- **Every experiment switch and environment variable that changes behavior when set:**
  - environment variables: F2_* / F3_* / the plain search names via search_env and SearchConfig, NEUTRAL, the COLMDP_* configuration, MAP_ITERS / ANNEAL_ITERS / CLIMB_ITERS / GOPT_STEPS;
  - macros: ITER_SCALE, SIM_HARNESS.

  Each must still work as documented, so that experiments can be repeated.
- The DesignStore, CLOCK_SCALE, the emergency design, and the section markers with the table of
  contents.

## Remove or simplify

- **Truly dead code that no switch or input can reach:** unused functions, variables, struct fields,
  parameters, and branches whose condition is constant in every configuration.
- **Duplicated logic** where merging is simple and keeps the output identical.
- **Superfluous comments:**
  - history notes ("esw-ptune: 0.6 -> 0.7", "esw-fast: ...", which version or PR introduced what) unless they explain a design choice;
  - comments that repeat the code;
  - stale comments that describe removed behavior.

  Keep the explanations of what each part does and its non-obvious invariants, concise. Keep the
  documentation of each switch.

Then verify as in the first brief, and in addition:
- with LOCAL_BENCH, every stderr line except the `*_sec` timings and the profiler outputs is
  identical between esw-speed and esw-clean on the 2000-seed compare;
- spot-check that a few switches still give identical results in both versions on a small range,
  e.g. `F2_MODE=2`, `COLMDP=0`, `MAP_ITERS=225000` with `--seeds 0-24`.

## Report

`solutions/esw-clean/README.md` in Japanese:
- first line: 改良元: solutions/esw-speed;
- what was removed or simplified, and what was intentionally kept;
- the line count before and after;
- the verification run-ids and results.

Final message: a 10-line summary.
