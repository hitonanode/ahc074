#!/usr/bin/env python3
"""焼きなましの手ごとにRDTSCの内訳を測る診断コピーを作る。"""
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
for name, path in [('base',ROOT/'solutions/astra-assign/main.cpp'),('main',HERE/'main.cpp')]:
    s = path.read_text()
    s = s.replace('        ANNEAL_TARGET void run(double seconds, int fixedIterations) {', '''        struct Meter {
            u64* cycles; u64* calls; bool sample; u64 start;
            Meter(u64* c, u64* n, bool s) : cycles(c), calls(n), sample(s), start(s ? __rdtsc() : 0) {}
            ~Meter() { if (sample) { *cycles += __rdtsc() - start; ++*calls; } }
        };
        ANNEAL_TARGET void run(double seconds, int fixedIterations) {
            const u64 anneal_total_start = __rdtsc();
            u64 cycles[7] = {}, calls[7] = {};
''')
    s = s.replace('                int type = rng.below(1000);', '''                int type = rng.below(1000);
                int slot = type < 150 ? 0 : type < 170 ? 1 : type < 270 ? 2 : type < 430 ? 3 : type < 750 ? 4 : type < 900 ? 5 : 6;
                Meter meter(cycles + slot, calls + slot, (it & 255) == 17);''')
    s = s.replace('            unit = best;', '''            std::cerr << "profile_stride = 256\\nanneal_total_ticks = " << (__rdtsc() - anneal_total_start) << '\\n';
            for (int i = 0; i < 7; ++i) std::cerr << "cycles_" << i << " = " << cycles[i] << "\\ncalls_" << i << " = " << calls[i] << '\\n';
            unit = best;''')
    a = s.index('WindowStats assign_windows(')
    b = s.index('// kBitLanes',a)
    part = s[a:b]
    part = part.replace('    WindowStats stats;', '''    WindowStats stats;
    struct Timer {
        u64& sum; u64 start;
        Timer(u64& v) : sum(v), start(__rdtsc()) {}
        ~Timer() { sum += __rdtsc() - start; }
    };
    u64 propose_ticks = 0, match_ticks = 0, apply_ticks = 0;
    const u64 map_start_ticks = __rdtsc();
''',1)
    for label, marker in [('propose','    auto propose = '),('match','    auto matching_cost = '),('apply','    auto apply_move = ')]:
        at = part.index('{',part.index(marker)) + 1
        part = part[:at] + f'\n        Timer profile_scope({label}_ticks);' + part[at:]
    at = part.rindex('    return stats;')
    part = part[:at] + '''
    std::cerr << "map_total_ticks = " << (__rdtsc() - map_start_ticks)
              << "\\nmap_propose_ticks = " << propose_ticks
              << "\\nmap_match_ticks = " << match_ticks
              << "\\nmap_apply_ticks = " << apply_ticks
              << "\\nassign_sec = " << CLOCK_SCALE * std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count() << '\\n';
''' + part[at:]
    s = s[:a] + part + s[b:]
    (HERE / f'profile-{name}.cpp').write_text(s)
