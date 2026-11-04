# Task 9 for Astra: refactor the new best solution without changing its behavior (esw-clean)

The window-assignment research (task 8) is stopped. The user wants to close this round of work with a
refactoring of the new best solution. Rules as before:
- run test cases only through `scripts/pahcer_run.py ... --no-record`;
- edit only inside `solutions/esw-clean/`;
- no commits;
- no edits to `scripts/`, `pahcer/`, other solutions or `trial_log.md`.

## The base

`solutions/esw-speed/main.cpp` (9232 lines) is the new best. It is climb4-fast plus three diffs:
- the exact window-assignment speedups (`solutions/design-fast`, another agent);
- your anneal-fast;
- your opsearch-fast3.

2000-seed normal compare vs climb4-fast (run 20261105-080311): identical designs, −0.008 ± 0.001%,
mean real time 1.661 → 1.364 s, end_sec > 2.0 s in 54 → 3 cases. Its designs are saved; use
`--design-from 20261105-080311_esw-speed`.

## Goal

`solutions/esw-clean/main.cpp`: the same program, cleaned. The user's words: remove dead code, reduce
superfluous comments, raise the quality, reduce the number of lines.

**The output must stay byte-identical for every input.** Keep:
- the same algorithm, iteration counts, random seeds and candidate orders;
- the same floating-point operation order wherever a decision depends on it.

Remove (as far as the code allows):
- **Research switches that select non-default behavior.** Hard-code the defaults and delete the
  alternative code paths and unused config fields:
  - environment variables: `search_env` / `SearchConfig` (F2_*, the plain names, F2_MODE), F3_*, `NEUTRAL`, the COLMDP_* configuration, `MAP_ITERS` / `ANNEAL_ITERS` / `CLIMB_ITERS` / `GOPT_STEPS`;
  - macros: `ITER_SCALE`, `SIM_HARNESS`.
- **Research logs and profilers:**
  - the heavy traces (`heavy_log`, `#heavy` / `#heavycand`, trace/predict paths);
  - the profilers: `COLFAST_PROFILE` / `CF_SCOPE` / `cf_report`, `AF_PROFILE`, `F3_PROFILE`, design-fast's profiling macros, and any other compile-time switch off by default.
- **Statistics counters printed only for past experiments.** Keep a compact set of useful `name = value` metrics:
  - the stage end times (`map_end_sec`, `anneal_end_sec`, `climb_end_sec`, `match_end_sec`, `perforation_end_sec`, `helper_end_sec`), `req_sec`, `end_sec`;
  - `gobj_after`, `model_cost` and its parts, `proxy_after`, `G`;
  - `total_moves`, `generic_moves`, `self_wrong`, `op_label_errors`, `design_loaded`;
  - whatever the DesignStore replays.

  `scripts/pahcer_run.py` reads `end_sec`. `scripts/observe.py` reads the `@paper` / `@ops` lines and aggregates `name = value` lines.
- **Unused functions, variables and branches.**
- **Comments:** keep short explanations of what each part does and its non-obvious invariants. Drop history notes ("esw-ptune: 0.6 -> 0.7", "esw-fast: ...", which version or PR introduced what) unless they explain a design choice.

Keep:
- the CLOCK_SCALE handling (`scaled_since`);
- under LOCAL_BENCH: the DesignStore (`--save-design` / `--design-from` must keep working), the
  `@paper` / `@ops` analysis output with its labels, and `design_loaded`;
- the emergency design;
- the section markers `// ==== <name> ====` with the table of contents in the header comment (update both if parts merge or disappear);
- a one-line note in the header that the time-shortage fallback was removed on purpose (PR #117) and must be restored before a final submission.

Quality: clear structure, no duplicated logic where merging is simple, consistent naming; C++23,
compiles with g++ and clang++ (`-std=c++23 -O2`, with and without `-DLOCAL_BENCH`), no
`bits/stdc++.h`, no new warnings under `-Wall -Wextra`.

## Verify

1. Normal compare on all 2000 seeds:
   ```sh
   scripts/pahcer_run.py --compare solutions/esw-speed solutions/esw-clean --no-record -c "..."
   ```
   Expect 0/2000/0 and WA 0. Byte-compare every `runs/<id>_esw-speed/out/*.txt` with
   `runs/<id>_esw-clean/out/*.txt`, and every `@paper` / `@ops` line of the err files.
2. Fixed designs (the design loading path):
   ```sh
   scripts/pahcer_run.py --compare solutions/esw-speed solutions/esw-clean --design-from 20261105-080311_esw-speed --seeds 0-200 --orders 2 --no-record -c "..."
   ```
   All outputs identical.
3. Timing: `req_sec` / `end_sec` means of both arms in the same compare should not get worse.

## Report

- `solutions/esw-clean/README.md` in Japanese:
  - first line: 改良元: solutions/esw-speed;
  - what was removed or simplified;
  - the line count before and after;
  - the verification run-ids and results;
  - the remaining stderr metrics and their meanings.
- Final message: a 10-line summary.
