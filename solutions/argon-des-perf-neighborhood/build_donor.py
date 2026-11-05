"""Condition donor differences also when the flipped color touches the target's holes."""
from pathlib import Path

root = Path(__file__).resolve().parent.parent
base = (root / 'argon-des-perf-gaincache/main.cpp').read_text()
old = '''                std::array<double, 65> edge;
                const u64 valid = edge_column(u, samples[i], c, edge);
                double value = q.avoid[c];
                for (u64 z = valid; z; z &= z - 1) {
                    const int lo = __builtin_ctzll(z);
                    value = std::max(value, q.forward[lo] + edge[lo] + q.backward[c + 1]);
                }
                values[i] = value;'''
for name, dimension in [('argon-des-perf-donorhole', 'changed_handle'),
                        ('argon-des-perf-donorcolumn', 'c')]:
    out = root / name
    assert not out.exists(), name
    out.mkdir()
    source = base.replace('    double last_owner_raw = 0, last_owner_corrected = 0;', '''    double last_owner_raw = 0, last_owner_corrected = 0;
    double last_donor_correction = 0, accepted_donor_correction = 0;
    long long donor_changed_samples = 0, donor_full_samples = 0;''')
    source = source.replace('        last_owner_raw = last_owner_corrected = 0;', '''        last_owner_raw = last_owner_corrected = 0;
        last_donor_correction = 0;''')
    assert old in source
    source = source.replace(old, '''                auto column_value = [&](u64 color) {
                    std::array<double, 65> edge;
                    const u64 valid = edge_column(u, color, c, edge);
                    double value = q.avoid[c];
                    for (u64 z = valid; z; z &= z - 1) {
                        const int lo = __builtin_ctzll(z);
                        value = std::max(value, q.forward[lo] + edge[lo] + q.backward[c + 1]);
                    }
                    return value;
                };
                const double value = column_value(samples[i]);
                ++donor_changed_samples;
                const int dimension = ''' + dimension + ''';
                const u64 flipped = samples[i] ^ (1ULL << dimension);
                // A covered h_c only changes this column's donor price. A target hole
                // can change other donor intervals, so both full DPs must be solved.
                const bool local = dimension == c && (opacity[s.ded[u]] >> c & 1);
                if (!local) ++donor_full_samples;
                const double flip_new = local ? column_value(flipped) : solve_edges(make_edges(u, flipped));
                const u64 saved_opacity = opacity[k];
                opacity[k] = cache_opacity[k];
                const double flip_old = local ? column_value(flipped) : solve_edges(make_edges(u, flipped));
                opacity[k] = saved_opacity;
                const int color = int(samples[i] >> dimension & 1);
                last_donor_correction += probability[dimension][color ^ 1] *
                    (flip_new - flip_old - (value - q.value));
                values[i] = value;''')
    source = source.replace('''        if (cache_opacity[k] & changed) {
            // Adding''', '''        last_donor_correction /= kSamples;
        if (cache_opacity[k] & changed) {
            // Adding''')
    source = source.replace('double upper = sum / kSamples - profit;',
                            'double upper = sum / kSamples - profit + last_donor_correction;')
    source = source.replace('const double correction = last_owner_corrected - last_owner_raw;',
                            'const double correction = last_owner_corrected - last_owner_raw + last_donor_correction;')
    source = source.replace('                accepted_donor += next - profit - last_owner_raw;', '''                accepted_donor += next - profit - last_owner_raw;
                accepted_donor_correction += last_donor_correction;''')
    source = source.replace('    perforation.install();', '''    std::cerr << "perf_donor_conditioned = " <<
        (perforation.accepted_donor + perforation.accepted_donor_correction) / P
              << "\\nperf_donor_correction = " << perforation.accepted_donor_correction / P
              << "\\nperf_donor_changed_samples = " << perforation.donor_changed_samples
              << "\\nperf_donor_full_samples = " << perforation.donor_full_samples << '\\n';
    perforation.install();''')
    (out / 'main.cpp').write_text(source)
    (out / 'README.md').write_text(f'''改良元: solutions/argon-des-perf-gaincache

donor側の差分も、{'穴を開ける窓' if dimension == 'changed_handle' else 'donor列の窓'}の色の両側を計算して条件付けする。
目標紙に穴があって他のdonor区間も影響を受ける場合は、変更前後の全列DPを再計算する。
目標がdonor列の窓を覆う場合は、従来の1列再評価を使う。
受理式と上限には補正差分を加え、元の色標本のキャッシュと差分再構築は維持する。
係数0.7、標本数8、候補順は基準と同じ。未来の注文は使わない。

perf_donor_conditioned / perf_donor_correctionは受理した候補の補正後donor利益と補正量（手/注文）。
perf_donor_changed_samples / perf_donor_full_samplesは評価した標本数と全列DPが必要だった標本数。
追加の環境変数はない。全既存ログ・@paper/@ops・プロファイラ・予算スイッチ、CLOCK_SCALE、
LOCAL_BENCH、DesignStore、段の目印と目次を保持する。
''')
    (out / '.gitignore').write_text('/__pycache__/\n')
