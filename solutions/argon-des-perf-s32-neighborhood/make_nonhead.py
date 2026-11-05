"""Port the runner-up mixture to the compact 32-stratum perforation model.

No evaluation is started here. The primary head pass is left identical; the
runner-up's identities are stratified too, avoiding two noisy Bernoulli hits.
"""
from pathlib import Path

root = Path(__file__).resolve().parent.parent
base = (root / 'argon-des-design-packed/main.cpp').read_text()
builder = (root / 'argon-des-perforation/build_variant.py').read_text()
block = builder[builder.index("replace('    int trials"):builder.index('source=source[:start]')]
block = block.replace('std::array<double, 65>', 'std::array<double, Capacity + 1>')
block = block.replace('std::array<std::vector<int>, 128>', 'std::array<std::vector<int>, 2 * Capacity>')
block = block.replace('std::array<int, 128>', 'std::array<uint8_t, 2 * Capacity>')
old = "replace('''            const double next = viable ? total_profit(k) : profit;''','''            if (wide && viable) ++secondary_viable;\n            const double next = viable ? total_profit(k) : profit;''')"
new = "replace('''            const double next = viable ? total_profit(k, weight > 0 ? delta / weight : 1e100) : profit;''','''            if (wide && viable) ++secondary_viable;\n            const double next = viable ? total_profit(k, weight > 0 ? delta / weight : 1e100) : profit;''')"
assert old in block
block = block.replace(old, new)

for suffix, rate in [('nonhead32', '.0625'), ('nonhead32wide', '.125')]:
    out = root / ('argon-des-perf-' + suffix)
    assert not out.exists(), out
    start = base.index('template<int Capacity>\nstruct Perforation {')
    end = base.index('// ==== Design state:', start)
    s = base[start:end]

    def replace(old, new):
        global s
        assert old in s, old[:100]
        s = s.replace(old, new)

    exec(block)
    replace('double secondary_rate = env_real("ARGON_D2_RATE", 0.125);',
            f'static constexpr double secondary_rate = {rate};')
    replace('int secondary_width = std::max(2, int(env_real("ARGON_D2_WIDTH", 2)));',
            'static constexpr int secondary_width = 2;')
    replace('double secondary_cost = 0, secondary_profit = 0;',
            'double secondary_cost = 0, secondary_profit = 0, secondary_corrected = 0;')
    replace('secondary_profit += next - profit;',
            'secondary_profit += next - profit;\n                    secondary_corrected += next - profit + correction;')
    replace('int h, const QueryCache& q) const {',
            'int h, const QueryCache& q, int sample) const {')
    replace('edge_column(u, color, c, edge)', 'edge_column(u, color, c, edge, sample)')
    replace('changed_handle, q)', 'changed_handle, q, i)')
    replace('edge_column(u, samples[i] ^ changed, changed_handle, old_edge)',
            'edge_column(u, samples[i] ^ changed, changed_handle, old_edge, i)')
    replace('''            for (auto& row : sample_head) {
                const double x = (random() >> 11) * 0x1.0p-53;
                int j = x < 1-rate ? 0 : 1 + std::min(int(list.size())-2, int((x-(1-rate))/rate*(list.size()-1)));
                row[2*c+b] = list[j];
            }''', '''            for (int u = 0; u < P; ++u) {
                std::array<int, kSamples> strata;
                std::iota(strata.begin(), strata.end(), 0);
                std::shuffle(strata.begin(), strata.end(), random);
                for (int t = 0; t < kSamples; ++t) {
                    const double x = (strata[t] + (random() >> 11) * 0x1.0p-53) / kSamples;
                    const int j = x < 1-rate ? 0 : 1 + std::min(int(list.size())-2, int((x-(1-rate))/rate*(list.size()-1)));
                    sample_head[u * kSamples + t][2*c+b] = list[j];
                }
            }''')
    source = base[:start] + s + base[end:]
    old = '''        Perforation<Capacity> perforation(solver);
        perforation.run(0.7);'''
    assert old in source
    source = source.replace(old, '''        Perforation<Capacity> perforation(solver);
        perforation.prepare_secondary();
        perforation.run(0.7);
        const double d2_start = elapsed_sec();
        perforation.enable_secondary();
        perforation.run(0.7);
        std::cerr << "d2_trials = " << perforation.secondary_trials
                  << "\\nd2_viable = " << perforation.secondary_viable
                  << "\\nd2_accepted = " << perforation.secondary_accepted
                  << "\\nd2_cost_delta = " << perforation.secondary_cost / P
                  << "\\nd2_profit_delta = " << perforation.secondary_profit / P
                  << "\\nd2_corrected_delta = " << perforation.secondary_corrected / P
                  << "\\nd2_sec = " << elapsed_sec() - d2_start << '\\n';''')
    out.mkdir()
    (out / 'main.cpp').write_text(source)
    (out / 'README.md').write_text(f'''改良元: solutions/argon-des-design-packed

基準と同じheadの穿孔の後、各列・色の2番目の紙も候補にする。
2番目の露出確率を{rate}、先頭を残りとする紙IDの32層化標本を使う。
色は基準の32層化標本。所有目標の色条件付け、上限と差分キャッシュを保持する。
追加段も係数0.7。追加段に入る際に、現在の穴数から色確率と標本を一度作り直す。
固定headの穴は追加段では変更しない。未来の注文は使わない。

d2_trials/viable/acceptedは追加段の候補数・事前評価通過数・受理数。
d2_cost_delta/profit_delta/corrected_deltaは穴コスト・未補正利益・補正利益の変化（手/注文）。
d2_secは追加段の時間。追加の環境変数はない。
既存のログ・@paper/@ops・プロファイラ・予算スイッチ、CLOCK_SCALE、LOCAL_BENCH、
DesignStore、段の目印と目次を保持する。
''')
