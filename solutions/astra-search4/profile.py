#!/usr/bin/env python3
"""時間の内訳を調べる診断コピーを作る。性能比較には使わない。"""
from pathlib import Path
import re
p=Path(__file__).resolve().parent
s=(p.parent/'imp-combo/main.cpp').read_text()
s=s.replace('    auto matching_cost =', '''    double prof_propose = 0, prof_transfer = 0, prof_swap = 0, prof_match = 0, prof_eval = 0;
    struct Profiler {
        double& sum;
        std::chrono::steady_clock::time_point begin = std::chrono::steady_clock::now();
        explicit Profiler(double& s): sum(s) {}
        ~Profiler() { sum += CLOCK_SCALE * std::chrono::duration<double>(std::chrono::steady_clock::now()-begin).count(); }
    };
    auto matching_cost =''',1)
s=s.replace('        std::array<int, 256> low{};', '        Profiler timer(prof_match);\n        std::array<int, 256> low{};',1)
s=s.replace('        if (screen_dirty) {', '        Profiler timer(prof_swap);\n        if (screen_dirty) {',1)
s=s.replace('        uint32_t ones = 0, twos = 0, four = 0;', '        Profiler timer(prof_transfer);\n        uint32_t ones = 0, twos = 0, four = 0;',1)
s=s.replace('    auto propose = [&](Move& mv) {', '''    auto eval = [&]<bool TwoEdges>(u64 erase, u64 ma, u64 mb, u64 fa, u64 fb) {
        Profiler timer(prof_eval);
        return evaluate_move<TwoEdges>(pairs, relations, pol, erase, ma, mb, fa, fb,
                                      ndir.data(), nrel.data(), valid.data(), pending.data());
    };
    auto propose = [&](Move& mv) {
        Profiler timer(prof_propose);''',1)
s=re.sub(r'evaluate_move<(true|false)>\(pairs, relations, pol, (.*?),\s*ndir.data\(\), nrel.data\(\), valid.data\(\), pending.data\(\)\)',r'eval.template operator()<\1>(\2)',s,flags=re.S)
s=s.replace('    stats.gobj_after = cur;', '''    std::cerr << "profile_propose_sec = " << prof_propose << "\\nprofile_transfer_sec = " << prof_transfer
              << "\\nprofile_swap_sec = " << prof_swap << "\\nprofile_match_sec = " << prof_match
              << "\\nprofile_eval_sec = " << prof_eval << '\\n';
    stats.gobj_after = cur;''',1)
(p/'profile.cpp').write_text(s)
