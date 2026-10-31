"""Builds an analysis copy of a solution (third audit, audit3-).

usage: mk_probe.py <solution main.cpp> <out.cpp>

The copy has the same moves as the solution unless the environment asks for an analysis:
  - la_process.inc replaces process(): the plan options (build_opts, a copy of the option loops of
    process() in audit2-blk / left-ap / audit3-narrow), the plan search returning every valid plan
    with its end state (plan_cands) and the choice. LA_MARGIN=m (>= 0) re-chooses among the distinct
    end states within m of the best plan cost by an exhaustive one-step lookahead: moves now + the
    mean over all 255 next targets (LA_N to sample) of the best plan cost of the next request
    (LA_PHI=0: its moves only). LA_LOG=1 prints the changed choices (LACH lines).
  - fm.inc: FM=n runs, before every n-th request, every legal first move (visible paper x every
    depth, the bookkeeping of the papers out of their columns repaired) followed by the plan search,
    and prints an FM line when one beats the plan search alone; FM_SHOW=r prints both plans of
    request r.
Build the result with g++ -std=c++23 -O2 and run it on tools/in/<seed>.txt directly (the input holds
the requests), with HUB_ANNEAL / CLIMB_ITERS fixed (see runner.py).
"""
import sys
from pathlib import Path

here = Path(__file__).resolve().parent
src, out = sys.argv[1], sys.argv[2]
s = open(src).read()
a = s.index("    std::vector<std::pair<int, int>> process(int u) {")
b = s.index("}  // namespace")
s = s[:a] + (here / "la_process.inc").read_text() + "\n" + s[b:]
anchor = "    const double kLaMargin = env_double(\"LA_MARGIN\", -1);"
assert s.count(anchor) == 1
s = s.replace(anchor, (here / "fm.inc").read_text() + anchor)
old = "        auto ops = solver.process(u);"
new = ("        if ((solver.kFm && t % solver.kFm == 0) || t == env_int(\"FM_SHOW\", -1)) solver.analyse_first_moves(u, t);\n"
       "        auto ops = solver.process(u);")
assert s.count(old) == 1
s = s.replace(old, new)
old = "    std::cerr << \"total_moves = \" << total << '\\n';"
new = old + """
    std::cerr << "la_req = " << solver.stat_la_req << "\\nla_changed = " << solver.stat_la_changed << "\\nla_gain = " << solver.stat_la_gain << '\\n';
    std::cerr << "fm_req = " << solver.fm_req << "\\nfm_better = " << solver.fm_better << "\\nfm_gain = " << solver.fm_gain << '\\n';"""
assert s.count(old) == 1
s = s.replace(old, new)
open(out, "w").write(s)
