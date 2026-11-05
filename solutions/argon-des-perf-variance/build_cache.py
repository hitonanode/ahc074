"""Keep unaffected target caches after accepting a single perforation."""
from pathlib import Path

root = Path(__file__).resolve().parent.parent
out = root / 'argon-des-perf-gaincache'
assert not out.exists()
out.mkdir()
s = (root / 'argon-des-perf-gain70/main.cpp').read_text()
s = s.replace('    std::vector<QueryCache> cache;', '''    std::array<bool, P> cache_dirty{};
    long long cache_rows = 0, cache_skips = 0;
    std::vector<QueryCache> cache;''')
s = s.replace('''    void refresh_cache() {''', '''    void refresh_cache(bool all = true) {''')
old = '''        for (int u = 0; u < P; u++)
            for (int sample = 0; sample < kSamples; sample++) {
                int i = u * kSamples + sample;
                cache[i] = make_cache(make_edges(u, samples[i]));
            }'''
new = '''        for (int u = 0; u < P; u++) {
            // total_profit proved that unchanged signatures produce identical edges
            // for every sample. Head identities, colors and sample probabilities stay fixed.
            if (!all && !cache_dirty[u]) {
                cache_skips += kSamples;
                continue;
            }
            for (int sample = 0; sample < kSamples; sample++) {
                int i = u * kSamples + sample;
                cache[i] = make_cache(make_edges(u, samples[i]));
                ++cache_rows;
            }
        }'''
assert old in s
s = s.replace(old, new)
s = s.replace('''        std::vector<bool> same(P);
        for (int u = 0; u < P; u++) {''', '''        std::vector<bool> same(P);
        cache_dirty.fill(true);  // the changed paper's own targets always need rebuilding
        for (int u = 0; u < P; u++) {''')
old = '''            for (int b = 0; b < 2; b++)
                same[u] = same[u] && (signature(heads[c][b], opacity) == signature(heads[c][b], cache_opacity));'''
assert old in s
s = s.replace(old, old + '\n            cache_dirty[u] = !same[u];')
old = '''                refresh_cache();
                assert(std::abs(profit - cached_profit()) < 1e-7);'''
assert old in s
s = s.replace(old, old.replace('refresh_cache();', 'refresh_cache(false);'))
s = s.replace('    perforation.install();', '''    std::cerr << "perf_cache_rows = " << perforation.cache_rows
              << "\\nperf_cache_skips = " << perforation.cache_skips << '\\n';
    perforation.install();''')
(out / 'main.cpp').write_text(s)
(out / 'README.md').write_text('''改良元: solutions/argon-des-perf-condbound

穿孔の条件付きDP利益の受理係数を0.5から0.7へ変更する。
穴を採用した後のDPキャッシュは、影響を受ける目標だけ再構築する。
total_profitが比較した「同じ列の両headの合法区間開始点と被覆窓」が不変なら、
全標本で区間DPの辺も不変。既存キャッシュをそのまま再利用できる。
変更紙自身の目標は常に再構築し、初回は全目標を構築する。
headの選択・色・色標本とその確率が探索中に変わらないことを使う。
その他の候補、探索量、受理結果と浮動小数点の順序は維持する。

追加指標 `perf_cache_rows` / `perf_cache_skips` は、構築した目標×標本数と再利用した数。
追加の環境変数はない。全既存ログ・@paper/@ops・プロファイラ・予算スイッチ、
CLOCK_SCALE・LOCAL_BENCH・DesignStore・段の目印と目次を保持。未来の注文は使わない。
''')
(out / '.gitignore').write_text('/__pycache__/\n')
