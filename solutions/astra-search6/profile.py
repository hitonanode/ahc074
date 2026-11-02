from pathlib import Path
import re
h=Path(__file__).resolve().parent
s=(h.parent/'as5-g38/main.cpp').read_text()
s=s.replace('    auto matching_cost =', '''    double prof_propose=0, prof_transfer=0, prof_swap=0, prof_match=0, prof_eval=0, prof_windows=0;
    struct Profiler {
        double& sum;
        std::chrono::steady_clock::time_point begin = std::chrono::steady_clock::now();
        explicit Profiler(double& s): sum(s) {}
        ~Profiler() { sum += CLOCK_SCALE * std::chrono::duration<double>(std::chrono::steady_clock::now()-begin).count(); }
    };
    auto matching_cost =''',1)
s=s.replace('        std::array<int, 256> low{};', '        Profiler timer(prof_match);\n        std::array<int, 256> low{};',1)
s=s.replace('        if (screen_dirty) {','        Profiler timer(prof_swap);\n        if (screen_dirty) {',1)
s=s.replace('        uint32_t ones = 0, twos = 0, four = 0, eight = 0;', '        Profiler timer(prof_transfer);\n        uint32_t ones = 0, twos = 0, four = 0, eight = 0;',1)
s=s.replace('        Move probe{};', '        Profiler timer(prof_windows);\n        Move probe{};',1)
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
              << "\\nprofile_eval_sec = " << prof_eval << "\\nprofile_windows_sec = " << prof_windows << '\\n';
    stats.gobj_after = cur;''',1)
(h/'profile.cpp').write_text(s)
