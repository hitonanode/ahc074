"""Condition donor-column colors where their only effect is that column's price."""
from pathlib import Path

root = Path(__file__).resolve().parent.parent
out = root / 'argon-des-perf-donorprice'
assert not out.exists()
out.mkdir()
s = (root / 'argon-des-perf-condbound/main.cpp').read_text()
s = s.replace('    double last_owner_raw = 0, last_owner_corrected = 0;', '''    double last_owner_raw = 0, last_owner_corrected = 0;
    double last_donor_correction = 0, accepted_donor_correction = 0;
    long long donor_changed_samples = 0, donor_conditioned_samples = 0;''')
s = s.replace('        last_owner_raw = last_owner_corrected = 0;', '''        last_owner_raw = last_owner_corrected = 0;
        last_donor_correction = 0;''')
a = s.index('    double total_profit(int k, double required_gain)')
b = s.index('    // Everything from the current opacity', a)
p = s[a:b]
old = '''                std::array<double, 65> edge;
                const u64 valid = edge_column(u, samples[i], c, edge);
                double value = q.avoid[c];
                for (u64 z = valid; z; z &= z - 1) {
                    const int lo = __builtin_ctzll(z);
                    value = std::max(value, q.forward[lo] + edge[lo] + q.backward[c + 1]);
                }
                values[i] = value;'''
new = '''                auto changed_column_value = [&](u64 color) {
                    std::array<double, 65> edge;
                    const u64 valid = edge_column(u, color, c, edge);
                    double value = q.avoid[c];
                    for (u64 z = valid; z; z &= z - 1) {
                        const int lo = __builtin_ctzll(z);
                        value = std::max(value, q.forward[lo] + edge[lo] + q.backward[c + 1]);
                    }
                    return value;
                };
                const double value = changed_column_value(samples[i]);
                ++donor_changed_samples;
                if (opacity[s.ded[u]] >> c & 1) {
                    // The target covers h_c: changing its head color affects only
                    // the price of a donor ending at c, so the cached other edges stay valid.
                    ++donor_conditioned_samples;
                    const u64 flipped = samples[i] ^ (1ULL << c);
                    const double flip_new = changed_column_value(flipped);
                    const u64 saved_opacity = opacity[k];
                    opacity[k] = cache_opacity[k];
                    const double flip_old = changed_column_value(flipped);
                    opacity[k] = saved_opacity;
                    const int color = int(samples[i] >> c & 1);
                    last_donor_correction += probability[c][color ^ 1] *
                        (flip_new - flip_old - (value - q.value));
                }
                values[i] = value;'''
assert old in p
p = p.replace(old, new)
p = p.replace('''        if (cache_opacity[k] & changed) {
            // Adding''', '''        last_donor_correction /= kSamples;
        if (cache_opacity[k] & changed) {
            // Adding''')
p = p.replace('double upper = sum / kSamples - profit;', 'double upper = sum / kSamples - profit + last_donor_correction;')
s = s[:a] + p + s[b:]
s = s.replace('const double correction = last_owner_corrected - last_owner_raw;',
              'const double correction = last_owner_corrected - last_owner_raw + last_donor_correction;')
s = s.replace('                accepted_donor += next - profit - last_owner_raw;', '''                accepted_donor += next - profit - last_owner_raw;
                accepted_donor_correction += last_donor_correction;''')
s = s.replace('    perforation.install();', '''    std::cerr << "perf_donor_conditioned = " <<
        (perforation.accepted_donor + perforation.accepted_donor_correction) / P
              << "\\nperf_donor_changed_samples = " << perforation.donor_changed_samples
              << "\\nperf_donor_conditioned_samples = " << perforation.donor_conditioned_samples << '\\n';
    perforation.install();''')
(out / 'main.cpp').write_text(s)
(out / 'README.md').write_text('''改良元: solutions/argon-des-perf-condbound

D2のdonor側の条件付き差分。目標紙がdonor列の窓を覆う場合、その列頭色を反転しても
その列から取る紙の価格しか変わらない。既存DPと1列の辺で両色の差分を求め、色確率で平均する。
他の場合は従来の標本値を使う。自目標の補正、候補順、標本数8、係数0.5は維持する。
受理判定と利益上限にはdonorの補正も入れ、元の標本値のキャッシュはそのまま保持する。

`perf_donor_conditioned` は受理した候補の補正後のdonor利益（手/注文）。
`perf_donor_changed_samples` はdonorの再計算標本数、`perf_donor_conditioned_samples` は補正できた標本数。
追加の環境変数はない。既存ログ・指標・@paper/@ops・プロファイラ・予算スイッチ、
CLOCK_SCALE・LOCAL_BENCH・DesignStore・段の目印と目次を保持。未来の注文は使わない。
''')
(out / '.gitignore').write_text('/__pycache__/\n')
