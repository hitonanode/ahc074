"""Over-time D2 oracle: two holes together, wider donors, denser samples."""
from pathlib import Path
root=Path(__file__).resolve().parent.parent;out=root/'argon-des-perf-pairs'
assert not out.exists();out.mkdir()
s=(root/'argon-des-perf-dense/main.cpp').read_text()
s=s.replace('env_real("ARGON_D2_RATE", 0.125)','env_real("ARGON_D2_RATE", 0.25)').replace('env_real("ARGON_D2_WIDTH", 2)','env_real("ARGON_D2_WIDTH", 3)')
start=s.index('    void run(double weight) {',s.index('struct Perforation {'));end=s.index('    // The number of perforated handles.',start)
p=s[start:end]
p=p.replace('void run(double weight)', 'void run(double weight, bool pairs = false)')
p=p.replace('std::vector<std::pair<int, int>> candidates;  // (head, handle)','std::vector<std::pair<int, u64>> candidates;  // (paper, handles changed together)')
old='''            for (u64 bits = allowed[k] & low_bits(c); bits; bits &= bits - 1)
                candidates.push_back({k, __builtin_ctzll(bits)});'''
new='''            for (u64 bits = allowed[k] & low_bits(c); bits; bits &= bits - 1) {
                const u64 first = bits & -bits;
                if (!pairs) candidates.push_back({k, first});
                else for (u64 rest = bits & (bits - 1); rest; rest &= rest - 1)
                    candidates.push_back({k, first | (rest & -rest)});
            }'''
assert old in p;p=p.replace(old,new)
p=p.replace('for (auto [k, c] : candidates)', 'for (auto [k, bit] : candidates)')
p=p.replace('            const u64 bit = 1ULL << c;\n            bool remove = opacity[k] & bit;', '''            const u64 removed = opacity[k] & bit;
            auto adjust_counts = [&](int sign) {
                for (u64 bits = bit; bits; bits &= bits - 1) {
                    const int c = __builtin_ctzll(bits);
                    for (int u : owners[k]) counts[c][target[u] >> c & 1] += sign * (removed >> c & 1 ? 1 : -1);
                }
            };
            auto changed_cost = [&] {
                double value = 0;
                for (u64 bits = bit; bits; bits &= bits - 1) value += cost(__builtin_ctzll(bits));
                return value;
            };''')
p=p.replace('double old_cost = cost(c), old_separate = separate_profit();', 'double old_cost = changed_cost(), old_separate = separate_profit();')
p=p.replace('for (int u : owners[k]) counts[c][target[u] >> c & 1] += remove ? 1 : -1;', 'adjust_counts(1);')
p=p.replace('const double delta = cost(c) - old_cost;', 'const double delta = changed_cost() - old_cost;')
p=p.replace('for (int u : owners[k]) counts[c][target[u] >> c & 1] += remove ? -1 : 1;', 'adjust_counts(-1);')
s=s[:start]+p+s[end:]
old='''    perforation.enable_secondary();
    perforation.run(0.5);'''
assert old in s;s=s.replace(old,old+'''
    const double d2_single_delta = (perforation.secondary_cost - 0.5*perforation.secondary_profit)/P;
    const int d2_single_accepted = perforation.secondary_accepted;
    perforation.run(0.5, true);
    std::cerr << "d2_single_net = " << d2_single_delta
              << "\\nd2_pair_accepts = " << perforation.secondary_accepted - d2_single_accepted << '\\n';''')
(out/'main.cpp').write_text(s)
(out/'README.md').write_text('''改良元: solutions/esw-slim

D2の時間超過を許す測定版。基準のhead穿孔後、同色の上位3候補を扱う。
非head露出率0.25（ARGON_D2_RATE）、追加段は64標本（ARGON_D2_SAMPLES）。
単独穴の追加後、同じ非head紙のハンドル2個を同時に反転する近傍を全列挙する。
単独穴では利益がなくても、2穴で長い範囲を覆える相乗効果を調べる。
紙自身の追加表示費用、他の紙の目標への効用、区間DPの重なりを同時評価する。

スイッチと指標はargon-des-perforationと同じ。d2_single_netは単独穴後の予測差、
d2_pair_acceptsは2穴同時近傍の受理回数。既存ログ等は保持。
時間制限を超える場合は測定専用として--no-recordで実行する。
共通の検証報告はsolutions/argon-des-perforation/REPORT.md。
''')
