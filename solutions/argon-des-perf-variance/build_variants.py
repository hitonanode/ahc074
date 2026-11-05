"""D2 continuation: separately test variance reduction and the acceptance weight."""
from pathlib import Path

here = Path(__file__).resolve().parent
root = here.parent
base = (root / 'argon-des-perf-condbound/main.cpp').read_text()
variants = [
    ('argon-des-perf-variance', 128, 'independent', .5),
    ('argon-des-perf-samples32', 32, 'independent', .5),
    ('argon-des-perf-antithetic', 8, 'antithetic', .5),
    ('argon-des-perf-stratified', 8, 'stratified', .5),
    ('argon-des-perf-weight40', 8, 'independent', .4),
    ('argon-des-perf-weight60', 8, 'independent', .6),
]
old = '''        for (auto& bits : samples)
            for (int c = 0; c < H; c++)
                if ((random() >> 11) * 0x1.0p-53 < probability[c][1]) bits |= 1ULL << c;'''
for name, count, scheme, weight in variants:
    out = root / name
    if out != here:
        assert not out.exists(), name
        out.mkdir()
    source = base.replace('static constexpr int kSamples = 8;', f'static constexpr int kSamples = {count};')
    if scheme == 'antithetic':
        replacement = '''        // Pair U with 1-U: both samples have the original marginal distribution.
        for (int u = 0; u < P; ++u) for (int sample = 0; sample < kSamples; sample += 2)
            for (int c = 0; c < H; ++c) {
                const double draw = (random() >> 11) * 0x1.0p-53;
                if (draw < probability[c][1]) samples[u * kSamples + sample] |= 1ULL << c;
                if (1 - draw < probability[c][1]) samples[u * kSamples + sample + 1] |= 1ULL << c;
            }'''
    elif scheme == 'stratified':
        replacement = '''        // Each target/column uses one uniform draw per stratum; independent shuffles
        // preserve independence between columns within any individual sample.
        for (int u = 0; u < P; ++u) for (int c = 0; c < H; ++c) {
            std::array<int, kSamples> strata;
            std::iota(strata.begin(), strata.end(), 0);
            std::shuffle(strata.begin(), strata.end(), random);
            for (int sample = 0; sample < kSamples; ++sample) {
                const double draw = (strata[sample] + (random() >> 11) * 0x1.0p-53) / kSamples;
                if (draw < probability[c][1]) samples[u * kSamples + sample] |= 1ULL << c;
            }
        }'''
    else:
        replacement = old
    assert old in source
    source = source.replace(old, replacement)
    source = source.replace('    perforation.run(0.5);', f'''    const double initial_hole_cost = perforation.hole_cost;
    perforation.run({weight});
    const double predicted = (perforation.hole_cost - initial_hole_cost - {weight} *
        (perforation.accepted_owner_corrected + perforation.accepted_donor)) / P;
    std::cerr << "perf_samples = {count}\\nperf_weight = {weight}\\n"
              << "perf_delta_hole = " << (perforation.hole_cost - initial_hole_cost) / P
              << "\\nperf_predicted_delta = " << predicted << '\\n';''')
    (out / 'main.cpp').write_text(source)
    description = {
        'independent': '独立な色標本を使う（生成規則は基準と同じ）。',
        'antithetic': '一様乱数Uと1−Uを対にし、個々の標本の分布を保ちながら色の偏りを抑える。',
        'stratified': '目標・列ごとに一様分布を等分し、各区間から1個ずつ抽出して並べ替える。',
    }[scheme]
    (out / 'README.md').write_text(f'''改良元: solutions/argon-des-perf-condbound

D2の追加調査。穿孔の色標本数は{count}、受理係数は{weight}。
{description}
変更窓に対する自目標の条件付き差分と利益上限は基準のまま。
他の設計段、候補順、将来の注文を使わない条件は維持する。

追加指標 `perf_samples` / `perf_weight` は標本数と係数、
`perf_delta_hole` は採用穴の費用増、`perf_predicted_delta` は費用−重み付き利益（手/注文）。
既存のログ・指標・プロファイラ・スイッチ・@paper/@ops・CLOCK_SCALE・LOCAL_BENCH・DesignStore、
段の目印と目次を保持。追加の環境変数はない。
''')
    (out / '.gitignore').write_text('/__pycache__/\n')
