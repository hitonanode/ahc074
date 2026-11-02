#!/usr/bin/env python3
"""基準のコピーに計測フックを入れる。元の解法には書き込まない。"""
from pathlib import Path

root = Path(__file__).resolve().parent
s = (root.parent / 'as6-cap38p0/main.cpp').read_text()
s = s.replace('#include <vector>', '#include <vector>\n#include <iomanip>\n#include <fstream>')
s = s.replace('constexpr double kHelperGiveUp = 1.55;', 'constexpr double kHelperGiveUp = 1e9;')
s = s.replace('std::vector<std::pair<int, int>> process(int u) {', 'std::vector<std::pair<int, int>> base_process(int u) {')
# Collection is disabled during every hypothetical next request. No nested oracle.
s = s.replace('double future = kEndWeight * adaptive_next_cost();', 'collect_plan();\n            double future = kEndWeight * adaptive_next_cost();')
s = s.replace('double cost = ops.size() + kFillerCharge * fillers.size() + kEndWeight * adaptive_next_cost();', 'collect_plan();\n                double cost = ops.size() + kFillerCharge * fillers.size() + kEndWeight * adaptive_next_cost();')
s = s.replace('keep(ops.size() + kFillerCharge * fillers.size() + kEndWeight * adaptive_next_cost());', 'collect_plan();\n            keep(ops.size() + kFillerCharge * fillers.size() + kEndWeight * adaptive_next_cost());')
start = s.index('#ifdef SIM_HARNESS\n')
end = s.index('#endif', start) + len('#endif')
s = s[:start] + (root/'harness.inc').read_text() + s[end:]
at = s.index('\n};\n\n// Emergency design')
s = s[:at] + '\n' + (root/'oracle.inc').read_text() + s[at:]
(root/'research.cpp').write_text(s)
