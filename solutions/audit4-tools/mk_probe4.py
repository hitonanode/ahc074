"""Builds an analysis copy of a solution (fourth audit, audit4-).

usage: mk_probe4.py <solution main.cpp> <out.cpp>

As solutions/audit3-tools/mk_probe.py (la_process.inc: process() split into the plan options, the
plan search returning every valid plan and the choice; fm.inc: FM=n, every legal first move before
every n-th request), plus fm2.inc:
  - describe(): the bookkeeping (lifted paper, fillers with levels and predecessors) rebuilt from the
    physical order alone, using the cyclic order of every column captured after the design.
    DSC=1 checks it against the bookkeeping of the solution after every request (dsc_* lines).
  - INS=n (INS_OFF=o): before every n-th request (t % n == o), for every prefix of the best plan
    (i moves), every legal move (visible paper x every depth) followed by the plan search from the
    rebuilt state, and the plan search alone from the prefix; INS lines for the gains.
  - PLAN_DBG=r: every plan option of request r with its outcome (PDBG lines).
  - TOGGLE=1 (compile with -DTOGGLE_PROBE, audit4-fix only): before every request, the best plan
    cost with the audit4 options (PRED_BOTTOM, GEN_FIX) off and on from the same state.
If the solution rebuilds its records after every request (audit4-fix: canonicalize), the copy of
process() does too. Run on tools/in/<seed>.txt directly with HUB_ANNEAL / CLIMB_ITERS fixed
(par.py; cls.py / show.py read the output).
"""
import sys
from pathlib import Path

here = Path(__file__).resolve().parent
a3 = here.parent / "audit3-tools"
src, out = sys.argv[1], sys.argv[2]
s = open(src).read()
a = s.index("    std::vector<std::pair<int, int>> process(int u) {")
b = s.index("}  // namespace")
la = (a3 / "la_process.inc").read_text()
if "void canonicalize()" in s:  # audit4-fix: the solution rebuilds its records after every request
    o1 = "        restore(cands[bi].st);\n        ops = cands[bi].ops;"
    assert la.count(o1) == 1
    la = la.replace(o1, "        restore(cands[bi].st);\n        if (kCanon) canonicalize();\n        ops = cands[bi].ops;")
    o2 = "    std::vector<std::pair<int, int>> process(int u) {\n        const State st0 = save();"
    assert la.count(o2) == 1
    la = la.replace(o2, "    std::vector<std::pair<int, int>> process(int u) {\n        if (cyc.empty()) init_cycles();\n        const State st0 = save();")
s = s[:a] + la + "\n" + s[b:]
anchor = "    const double kLaMargin = env_double(\"LA_MARGIN\", -1);"
assert s.count(anchor) == 1
s = s.replace(anchor, (a3 / "fm.inc").read_text() + (here / "fm2.inc").read_text() + anchor)
old = "        auto ops = solver.process(u);"
new = ("        if (t == 0) solver.a4_init_cycles();\n"
       "        if ((solver.kFm && t % solver.kFm == 0) || t == env_int(\"FM_SHOW\", -1)) solver.analyse_first_moves(u, t);\n"
       "        if (env_int(\"INS\", 0) && t % env_int(\"INS\", 1) == env_int(\"INS_OFF\", 0)) solver.analyse_insert(u, t);\n"
       "        if (t == env_int(\"PLAN_DBG\", -1)) solver.debug_plans(u);\n"
       "#ifdef TOGGLE_PROBE\n"
       "        if (env_int(\"TOGGLE\", 0)) solver.analyse_toggle(u, t);\n"
       "#endif\n"
       "        auto ops = solver.process(u);\n"
       "        if (env_int(\"DSC\", 0)) solver.check_describe();")
assert s.count(old) == 1
s = s.replace(old, new)
old = "    std::cerr << \"total_moves = \" << total << '\\n';"
new = old + """
#ifdef TOGGLE_PROBE
    std::cerr << "tg_req = " << solver.tg_req << "\\ntg_better = " << solver.tg_better << "\\ntg_worse = " << solver.tg_worse << "\\ntg_gain = " << solver.tg_gain << "\\ntg_dmoves = " << solver.tg_dm << '\\n';
#endif
    std::cerr << "fm_req = " << solver.fm_req << "\\nfm_better = " << solver.fm_better << "\\nfm_gain = " << solver.fm_gain << '\\n';
    std::cerr << "dsc_req = " << solver.dsc_req << "\\ndsc_bad = " << solver.dsc_bad << "\\ndsc_pred = " << solver.dsc_pred << '\\n';
    std::cerr << "ins_req = " << solver.ins_req << "\\nins_better = " << solver.ins_better << "\\nins_gain = " << solver.ins_gain
              << "\\nins_restart_better = " << solver.ins_restart_better << "\\nins_evals = " << solver.ins_evals << "\\nins_dmoves = " << solver.ins_dm << '\\n';"""
assert s.count(old) == 1
s = s.replace(old, new)
open(out, "w").write(s)
