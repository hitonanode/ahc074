"""Recheck runner-up perforation with conditioned owner gains and incremental caches."""
from pathlib import Path
root = Path(__file__).resolve().parent.parent
base = (root / 'argon-des-perf-gaincache/main.cpp').read_text()
# Reuse the previous experiment's identity mixture, with current accounting and cache.
builder = (root / 'argon-des-perforation/build_variant.py').read_text()
block = builder[builder.index("replace('    int trials"):builder.index("source=source[:start]")]
block = block.replace("replace('''            const double next = viable ? total_profit(k) : profit;''','''            if (wide && viable) ++secondary_viable;\n            const double next = viable ? total_profit(k) : profit;''')", "replace('''            const double next = viable ? total_profit(k, weight > 0 ? delta / weight : 1e100) : profit;''','''            if (wide && viable) ++secondary_viable;\n            const double next = viable ? total_profit(k, weight > 0 ? delta / weight : 1e100) : profit;''')")
for name, rate in [('argon-des-perf-nonhead70', .0625), ('argon-des-perf-nonhead70wide', .125)]:
    out = root / name
    assert not out.exists(), name
    start = base.index('struct Perforation {')
    end = base.index('// ==== Design state:', start)
    s = base[start:end]
    def replace(old, new):
        global s
        assert old in s, old[:100]
        s = s.replace(old, new)
    exec(block)
    s = s.replace('double secondary_rate = env_real("ARGON_D2_RATE", 0.125);', f'static constexpr double secondary_rate = {rate};')
    s = s.replace('int secondary_width = std::max(2, int(env_real("ARGON_D2_WIDTH", 2)));', 'static constexpr int secondary_width = 2;')
    # Calls introduced by the owner color conditioning, absent in the older prototype.
    s = s.replace('make_edges(u, samples[i] ^ changed)', 'make_edges(u, samples[i] ^ changed, i)')
    s = s.replace('edge_column(u, samples[i] ^ changed, changed_handle, old_edge)',
                  'edge_column(u, samples[i] ^ changed, changed_handle, old_edge, i)')
    s = s.replace('    double secondary_cost = 0, secondary_profit = 0;',
                  '    double secondary_cost = 0, secondary_profit = 0, secondary_corrected = 0;')
    s = s.replace('                    secondary_profit += next - profit;',
                  '                    secondary_profit += next - profit;\n                    secondary_corrected += next - profit + correction;')
    source = base[:start] + s + base[end:]
    source = source.replace('''    Perforation perforation(solver);
    perforation.run(0.7);''', '''    Perforation perforation(solver);
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
    (out / 'README.md').write_text(f'''改良元: solutions/argon-des-perf-gaincache

基準のheadへの穿孔を係数0.7で終えた後、各列・色の2番目の紙も穿孔候補にする。
2番目の紙の露出確率を{rate}、headを残りの確率とする固定した紙ID標本を使う。
色は独立の8標本、owner側の色条件付けと上限、差分キャッシュは基準と同じ。
追加段でも係数0.7を使う。headは最初の設計で一度だけ決める。

追加のd2_trials/viable/acceptedは第2段の候補・事前評価通過・受理数。
d2_cost_delta/profit_delta/corrected_deltaは穴コスト・未補正利益・補正利益の変化（手/注文）。
d2_secは追加段の時間。追加の環境変数はない。
全既存ログ・@paper/@ops・プロファイラ・予算スイッチ、CLOCK_SCALE、LOCAL_BENCH、
DesignStore、段の目印と目次を保持する。
''')
    (out / '.gitignore').write_text('/__pycache__/\n')
