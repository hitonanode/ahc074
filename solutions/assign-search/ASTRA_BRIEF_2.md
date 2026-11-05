# Task 10, addendum: build on the history of this search (read before continuing)

Your run was stopped only to give you this; continue task 10 (`ASTRA_BRIEF.md`) afterwards, keeping
what you have.

The window-assignment search has been improved six times before (2026-11-02, a different Astra
session). Read these sections of `trial_log.md` before choosing directions, and do not repeat what
failed:
- 「2026-11-02 窓の割り当ての段の高速化（astra-assign、astra-anneal）」
- 「2026-11-02 窓の割り当ての探索の効率化（astra-search、astra-search2、imp-s2hd、imp-combo）」
- 「2026-11-02 手の内訳の分析 … 1 位との差を生む構造の調査（astra-struct）」
- 「2026-11-02 窓の割り当ての探索の 4〜6 回目（astra-search4〜6）と G = 38 / 39」

The solutions/astra-search* directories hold their sources and READMEs.

What those rounds found:
- astra-search, −0.628%:
  - colors drawn together with exchanges and transfers;
  - cheap pre-rejection of moves that break ≥ 4 (later 3) selected pairs;
  - reuse of the decisions and costs of repeated candidates.
- astra-search2: at a stall, move to the best exactly evaluated candidate and avoid the last reverse
  move (−0.26%).
- astra-search3: transfer destinations ranked directly.
- astra-search4: the 3-pair pre-rejection and tuned stall limits (−0.15%).
- astra-search5: batched exchange destinations per generic window (−0.05%).
- astra-search6: the compound "remove generic window a, add handle b to another sheet pair" move,
  1/16 of the exchanges (−0.05%).
- The gains shrank round by round: the easy algorithmic wins are taken.

What failed:
- **A sparse exact evaluation: +0.64%, discarded in astra-search.** You had started `add_sparse.py`.
  If it is the same idea, compare with that record first and say why yours differs.
- Pre-rejection at 2 pairs: +3.3%.
- Changing the exchange rate, the temperature, or the stall noise: flat.
- Distance limit 28; restarts (2–3 starts); a handle-difference weight by depth (map-depth).
- More greedy pairs (75 / 80).

From the same log: the "price" of the comparator compatibility constraint is about 5% of the score
(compat-price). The gain of the assignment comes almost entirely from choosing good pairs. This
suggests that ideas raising the number of cheap valid pairs (the matching is limited by validity:
about 160 valid pairs, 133 scanned for 71) are the most promising kind.

My result to use (pair-exact, merged): the greedy matching of the objective is nearly optimal. The
exact minimum-cost matching via biglib lowers gobj by only 0.0017 on average (0 in 152 of 200
seeds), and using it in Design::initialize changes nothing (+0.026 ± 0.071%). Do not spend time on
the matching itself.

Everything else in `ASTRA_BRIEF.md` holds:
- record the runs (no `--no-record`);
- keep all logs and switches;
- measure gobj at equal map time, then the score on 500 → 2000 seeds;
- write a Japanese README per solution and REPORT.md.
