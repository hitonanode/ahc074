"""The coefficient/sample neighborhood around the PR #139 base."""
from pathlib import Path

here = Path(__file__).resolve().parent
root = here.parent
base = (root / 'argon-des-perf-gaincache/main.cpp').read_text()
variants = [
    ('argon-des-perf-w65', 8, .65, False),
    ('argon-des-perf-w75', 8, .75, False),
    ('argon-des-perf-s32c70', 32, .7, False),
    ('argon-des-perf-s32c75', 32, .75, False),
    ('argon-des-perf-strata70', 8, .7, True),
    ('argon-des-perf-strata32', 32, .7, True),
]
old = '''        for (auto& bits : samples)
            for (int c = 0; c < H; c++)
                if ((random() >> 11) * 0x1.0p-53 < probability[c][1]) bits |= 1ULL << c;'''
stratified = '''        // A uniform draw in each stratum, independently shuffled for each target/column.
        for (int u = 0; u < P; ++u) for (int c = 0; c < H; ++c) {
            std::array<int, kSamples> strata;
            std::iota(strata.begin(), strata.end(), 0);
            std::shuffle(strata.begin(), strata.end(), random);
            for (int sample = 0; sample < kSamples; ++sample) {
                const double draw = (strata[sample] + (random() >> 11) * 0x1.0p-53) / kSamples;
                if (draw < probability[c][1]) samples[u * kSamples + sample] |= 1ULL << c;
            }
        }'''
for name, count, weight, strat in variants:
    out = root / name
    assert not out.exists(), name
    out.mkdir()
    source = base.replace('kSamples = 8;', f'kSamples = {count};')
    source = source.replace('perforation.run(0.7);', f'perforation.run({weight});')
    if strat:
        assert old in source
        source = source.replace(old, stratified)
    (out / 'main.cpp').write_text(source)
    (out / 'README.md').write_text(f'''改良元: solutions/argon-des-perf-gaincache

PR #139の動作点の近傍を調べる。穿孔の受理係数は{weight}、色標本数は{count}。
{'目標・列ごとに一様分布を等分して各区間から1個ずつ抽出し、独立な並べ替えを使う。' if strat else '色標本は基準と同じ独立抽出。'}
自目標の条件付き差分、利益上限、不変なDPキャッシュの再利用、候補順は維持する。
他の設計段・注文処理は変更しない。未来の注文は使わない。

新しい環境変数や指標はない。既存のperforation_*、perf_*で受理数・利益・キャッシュ計算量を確認できる。
既存ログ・@paper/@ops・プロファイラ・予算スイッチ、CLOCK_SCALE・LOCAL_BENCH・DesignStore、
段の目印と目次を保持する。
''')
    (out / '.gitignore').write_text('/__pycache__/\n')
(here / 'README.md').write_text('''改良元: solutions/argon-des-perf-gaincache

D2の動作点近傍を調べるための調査ディレクトリ。main.cppは基準と同じ。
係数・標本・donor条件付け・非head候補・前段の目的を別の候補に分けて検証する。
新しいスイッチや指標はない。共通の集計と実験記録をここに置く。
''')
(here / '.gitignore').write_text('/__pycache__/\n')
