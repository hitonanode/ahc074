from pathlib import Path
p=Path(__file__).resolve().parent
s=(p.parent/'tight-thirty-eight/main.cpp').read_text()
s=s.replace('    static constexpr int kAnnealSegments = 4;','''    struct ArchivedDesign { std::vector<Unit> units; std::vector<int> handles; };
    std::vector<ArchivedDesign> archives;
    static constexpr int kAnnealSegments = 4;''')
s=s.replace('            double bestCost = cur;\n            for (int it = 0;; it++) {','''            double bestCost = cur;
            int archive_step=1;
            for (int it = 0;; it++) {''')
s=s.replace('                    temp = 2.0 * std::pow(0.015 / 2.0, p0 + (p1 - p0) * progress);','''                    if(p0>=.5 && archive_step<=3 && progress>=archive_step*.25) {
                        D.archives.push_back({best,bestHandle});archive_step++;
                    }
                    temp = 2.0 * std::pow(0.015 / 2.0, p0 + (p1 - p0) * progress);''')
s=s.replace('            unit = best;\n            D.handle = bestHandle;','''            if(p0>=.5)D.archives.push_back({best,bestHandle});
            unit = best;
            D.handle = bestHandle;''')
(p/'main.cpp').write_text(s)
for name in ['common.hpp','saved.hpp']:(p/name).write_text((p.parent/'early-select'/name).read_text())
