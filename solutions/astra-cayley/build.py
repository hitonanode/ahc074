#!/usr/bin/env python3
from pathlib import Path

here=Path(__file__).resolve().parent
source=(here.parent/'astra-search4'/'main.cpp').read_text()
start=source.index('        dist.assign(n * n, 255);')
end=source.index('\n    // The orders (indices of perms)',start)
source=source[:start]+'''        // Complete comparison layers have exactly the nonbottom sheets visible.
        // Relabeling sheets is therefore an automorphism of this DIRECTED graph.
        // Relabel source[a][i] to i; every source-to-target distance is then an
        // identity-to-relative-target distance. Preserve the original dense table
        // so all callers and all tie-breaking remain unchanged.
        assert(M == 6 && n == 720);
        std::vector<uint8_t> identity(n, 255);
        std::vector<int> q(n);
        int qb = 0, qe = 0;
        q[qe++] = 0; identity[0] = 0;
        while (qb < qe) {
            int x = q[qb++];
            for (int y : next[x]) if (y >= 0 && identity[y] == 255)
                identity[y] = identity[x] + 1, q[qe++] = y;
        }
        assert(qe == n);
        std::vector<uint8_t> by_code(1U << 18, 255);
        for (int s = 0; s < n; s++) {
            unsigned code = 0;
            for (int j = 0; j < 6; j++) code |= unsigned(perms[s][j]) << (3 * j);
            by_code[code] = identity[s];
        }
        dist.resize(n * n);
        for (int a = 0; a < n; a++) {
            std::array<unsigned char, 6> inverse{};
            for (int j = 0; j < 6; j++) inverse[perms[a][j]] = j;
            for (int b = 0; b < n; b++) {
                unsigned code = 0;
                for (int j = 0; j < 6; j++) code |= unsigned(inverse[perms[b][j]]) << (3 * j);
                dist[a * n + b] = by_code[code];
            }
        }
    }
''' + source[end:]
(here/'main.cpp').write_text('// astra-cayley: exact one-source relabeling construction of the unchanged 720^2 distance table.\n'+source)
