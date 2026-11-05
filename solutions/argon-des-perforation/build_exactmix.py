"""Remove rare-donor sampling noise: exact identity mixture in every interval edge."""
from pathlib import Path
root=Path(__file__).resolve().parent.parent;out=root/'argon-des-perf-exactmix'
assert not out.exists();out.mkdir()
s=(root/'argon-des-perforation/main.cpp').read_text()
start=s.index('    __attribute__((target("popcnt"))) u64 edge_column(',s.index('struct Perforation {'))
body=s.index('        u64 valid = 0;',start)
insert='''        if (wide) {
            if (c == columns[s.ded[u]]) return 0;
            const u64 holes = low_bits(H) & ~opacity[s.ded[u]];
            const u64 bad_mask = (color ^ target[u]) & holes;
            std::array<std::vector<std::array<double, 65>>, 2> values;
            u64 all = 0;
            for (int b = 0; b < 2; ++b) for (int k : ranked[2*c+b]) {
                std::array<double, 65> row{};
                const u64 mask = opacity[k] & holes;
                const u64 wrong = mask & (colors[k] ^ target[u]);
                const int lo = wrong ? 64 - __builtin_clzll(wrong) : 0;
                const u64 covered = bad_mask & mask & ~low_bits(lo);
                int number = __builtin_popcountll(covered);
                const double price = 1.6 + (b != int(color >> c & 1));
                for (int j = lo; j <= c && number > price; ++j) {
                    row[j] = number - price;
                    all |= 1ULL << j;
                    number -= int(covered >> j & 1);
                }
                values[b].push_back(row);
            }
            for (u64 bits = all; bits; bits &= bits - 1) {
                const int lo = __builtin_ctzll(bits);
                double value = 0;
                for (int a = 0; a < int(values[0].size()); ++a)
                    for (int b = 0; b < int(values[1].size()); ++b)
                        value += exposure[ranked[2*c][a]] * exposure[ranked[2*c+1][b]] *
                            std::max(values[0][a][lo], values[1][b][lo]);
                edge[lo] = value;
            }
            return all;
        }
'''
s=s[:body]+insert+s[body:]
(out/'main.cpp').write_text(s)
(out/'README.md').write_text('''改良元: solutions/esw-slim

D2の追加穿孔。基準のhead穿孔を保ち、非head第2候補の露出率を0.125とする。
非headが現れるかを8標本から抽選する処理をやめ、各列の区間辺で両色の紙の組合せを全列挙して期待値を計算する。
色は従来の8標本。紙の同定の抽選誤差を除き、低頻度の候補の利益を過大評価しないための比較。
区間DPは期待辺利益を最大化する（期待される最大利益の厳密値とは異なる）。

ARGON_D2_RATE、ARGON_D2_WIDTHとd2_*指標はargon-des-perforationと同じ。
既存ログ・プロファイラ・CLOCK_SCALE・LOCAL_BENCH・DesignStore・段の目印を維持する。
共通報告はsolutions/argon-des-perforation/REPORT.md。
''')
