#!/usr/bin/env python3
"""元版と最終版の診断コピーを作る（通常の main.cpp は変更しない）。"""
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]

for name, src in [('base', ROOT / 'solutions/astra-assign/main.cpp'), ('main', HERE / 'main.cpp')]:
    s = src.read_text()
    s = s.replace('        double cur = 0, temp = 2.0;', '''        double cur = 0, temp = 2.0;
        u64 trace_hash = 0xcbf29ce484222325ULL, trace_count = 0;
        void trace_add(u64 x) { trace_hash = (trace_hash ^ x) * 0x100000001b3ULL; ++trace_count; }
        void trace_double(double x) { u64 bits; std::memcpy(&bits, &x, 8); trace_add(bits); }
''')
    old = '''        bool accept(double d) {
            return d <= 0 || d < temp * logs[D.rng.next() & 16383];
        }'''
    new = '''        ANNEAL_TARGET bool accept(double d) {
            trace_double(d); trace_double(temp); trace_double(cur); trace_add(D.rng.x);
            const bool accepted = d <= 0 || d < temp * logs[D.rng.next() & 16383];
            trace_add(accepted); trace_add(D.rng.x);
            return accepted;
        }'''
    assert old in s
    s = s.replace(old, new)
    s = s.replace('            unit = best;', '''            trace_double(cur); trace_double(bestCost); trace_add(D.rng.x);
            std::cerr << "trace_hi = " << (trace_hash >> 32) << "\\ntrace_lo = " << (trace_hash & 0xffffffffU)
                      << "\\ntrace_count = " << trace_count << '\\n';
            unit = best;''')
    a = s.index('WindowStats assign_windows(')
    b = s.index('// kBitLanes',a)
    part = s[a:b].replace('    WindowStats stats;', '''    WindowStats stats;
    u64 map_hash = 0xcbf29ce484222325ULL, map_count = 0;
    auto map_integer = [&](u64 x) { map_hash = (map_hash ^ x) * 0x100000001b3ULL; ++map_count; };
    auto map_double = [&](double x) { u64 bits; std::memcpy(&bits,&x,8); map_integer(bits); };
''',1)
    part = re.sub(r'(const double candidate = matching_cost\([^;]+;)', r'''\1
        map_double(candidate); map_double(cur); map_integer(rng.x);''',part)
    marker = '        if (candidate <= cur || rng.real()'
    part = part.replace(marker, '        map_double(temp); map_double(progress);\n' + marker)
    at = part.rindex('    return stats;')
    part = part[:at] + '''
    map_integer(rng.x); map_double(cur);
    std::cerr << "map_trace_hi = " << (map_hash >> 32) << "\\nmap_trace_lo = " << (map_hash & 0xffffffffU)
              << "\\nmap_trace_count = " << map_count << '\\n';
''' + part[at:]
    s = s[:a] + part + s[b:]
    (HERE / f'trace-{name}.cpp').write_text(s)
