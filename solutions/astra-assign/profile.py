#!/usr/bin/env python3
"""計測専用コピーを作る。提出用ソースには計測器を入れない。"""
from pathlib import Path
import sys

here = Path(__file__).resolve().parent
src = Path(sys.argv[1]).read_text()
if 'struct WindowRelations' in src:
    src = src.replace('    int cost(uint32_t r) {', '''
    unsigned long long cache_calls = 0, cache_hits = 0;
    ~WindowRelations() {
        std::cerr << "profile_cache_calls = " << cache_calls
                  << "\\nprofile_cache_hits = " << cache_hits << '\\n';
    }
    int cost(uint32_t r) {
        ++cache_calls;
''')
    src = src.replace('if (uint32_t(old >> 32) == r) return uint32_t(old);',
                      'if (uint32_t(old >> 32) == r) { ++cache_hits; return uint32_t(old); }')
begin = src.index('WindowStats assign_windows(')
end = src.index('// kBitLanes', begin)
part = src[begin:end]
marker = '    WindowStats stats;'
part = part.replace(marker, marker + '''
    struct ProfileTimer {
        unsigned long long& ticks;
        unsigned long long start;
        explicit ProfileTimer(unsigned long long& t) : ticks(t), start(__rdtsc()) {}
        ~ProfileTimer() { ticks += __rdtsc() - start; }
    };
    unsigned long long propose_ticks = 0, match_ticks = 0, apply_ticks = 0;
    unsigned long long match_calls = 0, match_candidates = 0, match_scanned = 0, apply_calls = 0;
    const auto profile_start = __rdtsc();
''', 1)
for label, marker in [('propose', '    auto propose = '), ('match', '    auto matching_cost = '),
                      ('apply', '    auto apply_move = ')]:
    at = part.index('{', part.index(marker)) + 1
    part = part[:at] + f'\n        ProfileTimer profile_scope({label}_ticks);' + part[at:]
part = part.replace('ProfileTimer profile_scope(apply_ticks);',
                    'ProfileTimer profile_scope(apply_ticks); ++apply_calls;')
for marker in ['        std::array<u64, 4> used{};', '        std::array<unsigned char, 256> used{};']:
    part = part.replace(marker, '''
        ++match_calls;
        match_candidates += size;
        match_scanned += size;
''' + marker)
part = part.replace('            if (++matched == need) break;',
                    '            if (++matched == need) { match_scanned -= size - i - 1; break; }')
at = part.rindex('    return stats;')
part = part[:at] + '''
    const auto profile_total_ticks = __rdtsc() - profile_start;
    const double profile_assign_sec = CLOCK_SCALE *
        std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count();
    std::cerr << "profile_propose_ticks = " << propose_ticks
              << "\\nprofile_match_ticks = " << match_ticks
              << "\\nprofile_apply_ticks = " << apply_ticks
              << "\\nprofile_match_calls = " << match_calls
              << "\\nprofile_match_candidates = " << match_candidates
              << "\\nprofile_match_scanned = " << match_scanned
              << "\\nprofile_apply_calls = " << apply_calls
              << "\\nprofile_total_ticks = " << profile_total_ticks
              << "\\nprofile_assign_sec = " << profile_assign_sec << '\\n';
''' + part[at:]
(here / sys.argv[2]).write_text(src[:begin] + part + src[end:])
