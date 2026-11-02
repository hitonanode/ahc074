#!/usr/bin/env python3
"""Add exact symmetry-compressed seven-sheet distance and generic look-ahead."""
from pathlib import Path

here = Path(__file__).resolve().parent
base = (here.parent / 'astra-research' / 'main.cpp').read_text()
source = base.replace('std::vector<uint8_t> dist;', '''std::vector<std::array<unsigned char, 7>> inverse7;
    std::vector<uint8_t> relative7;
    std::vector<std::vector<int>> previous7;
    std::vector<uint8_t> dist;''', 1)
source = source.replace('int distance(int a, int b) const { return dist[a * perms.size() + b]; }', '''int distance(int a, int b) const {
        if (M == 7) {
            unsigned code = 0;
            for (int j = 0; j < 7; j++) code |= unsigned(inverse7[a][perms[b][j]]) << (3 * j);
            return relative7[code];
        }
        return dist[a * perms.size() + b];
    }''')
needle = '        // next[a][pos * M + d]:'
pos = source.index(needle)
source = source[:pos] + '''        if (M == 7) {
            // Relabeling sheets is an automorphism of the complete comparison
            // graph, including the rule that the current bottom cannot move.
            auto encode = [](const std::vector<int>& p) {
                unsigned code = 0;
                for (int j = 0; j < 7; j++) code |= unsigned(p[j]) << (3 * j);
                return code;
            };
            std::vector<int> index(1U << 21, -1);
            inverse7.resize(n);
            for (int s = 0; s < n; s++) {
                index[encode(perms[s])] = s;
                for (int j = 0; j < 7; j++) inverse7[s][perms[s][j]] = j;
            }
            next.assign(n, std::vector<int>(49, -1));
            previous7.assign(n, {});
            for (int a = 0; a < n; a++) {
                previous7[a].reserve(42);
                for (int pos = 0; pos < 6; pos++) for (int d = 0; d < 7; d++) if (pos != d) {
                    auto q = perms[a];
                    int k = q[pos]; q.erase(q.begin() + pos); q.insert(q.begin() + d, k);
                    int b = index[encode(q)];
                    next[a][pos * 7 + d] = b;
                    previous7[b].push_back(a);
                }
            }
            std::vector<unsigned char> ds(n, 255);
            std::vector<int> queue(n); int head = 0, tail = 0;
            ds[0] = 0; queue[tail++] = 0;
            while (head < tail) {
                int a = queue[head++];
                for (int b : next[a]) if (b >= 0 && ds[b] == 255) ds[b] = ds[a] + 1, queue[tail++] = b;
            }
            assert(tail == n);
            relative7.assign(1U << 21, 255);
            for (int s = 0; s < n; s++) relative7[encode(perms[s])] = ds[s];
            return;
        }
''' + source[pos:]
needle = '            cnt++;\n            for (int s = 0; s < n; s++) {'
replacement = '''            cnt++;
            if (M == 7) {
                // Directed reverse BFS: distance FROM each start TO this target set.
                std::vector<unsigned char> ds(n, 255);
                std::vector<int> queue(n); int head = 0, tail = 0;
                for (int s : sat[u]) ds[s] = 0, queue[tail++] = s;
                while (head < tail) {
                    int s = queue[head++];
                    for (int t : comparator.previous7[s]) if (ds[t] == 255)
                        ds[t] = ds[s] + 1, queue[tail++] = t;
                }
                assert(tail == n);
                for (int s = 0; s < n; s++) future[s] += ds[s];
                continue;
            }
            for (int s = 0; s < n; s++) {'''
assert needle in source
source = source.replace(needle, replacement, 1)
needle = '        solver.init_lookahead();\n    }\n    std::cerr << "helper_end_sec = "'
replacement = '''        solver.init_lookahead();
    } else if (M == 7 && comp.complete) {
        solver.comparator.build_tables();
        solver.init_lookahead();
    }
    std::cerr << "helper_end_sec = "'''
assert needle in source
source = source.replace(needle, replacement, 1)
(here / 'main.cpp').write_text(source)
g40 = here.parent / 'astra-research-g40' / 'main.cpp'
g40.write_text(base.replace('#define RESEARCH_G 38', '#define RESEARCH_G 40'))
