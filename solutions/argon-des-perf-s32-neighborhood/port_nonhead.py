"""Port D2 only onto PR143; additionally test a single mixed-donor pass."""
from pathlib import Path

root = Path(__file__).resolve().parent.parent
oldbase = (root/'argon-des-design-packed/main.cpp').read_text()
base = (root/'argon-req-filterblocks-v2/main.cpp').read_text()

def extract(source, first, last):
    a, b = source.index(first), source.index(last)
    return source[a:b]

sections = [('template<int Capacity>\nstruct Perforation {', '// ==== Design state:'),
            ('    // ==== design_papers: handle perforation ====', '// ==== Saving and loading the design state')]

for rate, name in [('.0625', 'nonhead32'), ('.125', 'nonhead32wide')]:
    source = base
    previous = (root/f'argon-des-perf-{name}/main.cpp').read_text()
    for first, last in sections:
        before = extract(oldbase, first, last)
        assert source.count(before) == 1
        source = source.replace(before, extract(previous, first, last))
    out = root/f'argon-des-perf-{name}-v2'
    out.mkdir()
    (out/'main.cpp').write_text(source)
    readme = (root/f'argon-des-perf-{name}/README.md').read_text()
    (out/'README.md').write_text(readme.replace('改良元: solutions/argon-des-design-packed',
                                              '改良元: solutions/argon-req-filterblocks-v2'))

    # Initial rebuild chooses heads/ranks but does not need a DP yet. enable_secondary
    # rebuilds it once, after setting the identity mixture; run then visits all donors.
    start, end = source.index('template<int Capacity>\nstruct Perforation {'), source.index('// ==== Design state:')
    s = source[start:end]
    old = '        std::mt19937_64 random(731000003);'
    assert s.count(old) == 1
    s = s.replace(old, '        if (!wide) return;  // the only search uses the identity mixture\n' + old)
    old = 'if (wide ? (exposure[k] == 0 || k == heads[c][b]) : k != heads[c][b]) continue;'
    assert s.count(old) == 1
    s = s.replace(old, 'if (wide ? exposure[k] == 0 : k != heads[c][b]) continue;')
    nonhead = 'wide && k != heads[columns[k]][colors[k] >> columns[k] & 1]'
    s = s.replace('if (wide) ++secondary_trials;', f'if ({nonhead}) ++secondary_trials;')
    s = s.replace('if (wide && viable) ++secondary_viable;', f'if ({nonhead} && viable) ++secondary_viable;')
    s = s.replace('if (wide) {\n                    ++secondary_accepted;',
                  f'if ({nonhead}) {{\n                    ++secondary_accepted;')
    source = source[:start] + s + source[end:]
    old = '''        perforation.prepare_secondary();
        perforation.run(0.7);
        const double d2_start = elapsed_sec();'''
    assert source.count(old) == 1
    source = source.replace(old, '''        perforation.prepare_secondary();
        const double d2_start = elapsed_sec();''')
    mixname = 'headmix32' + ('wide' if name.endswith('wide') else '')
    out = root/f'argon-des-perf-{mixname}'
    out.mkdir()
    (out/'main.cpp').write_text(source)
    (out/'README.md').write_text(f'''改良元: solutions/argon-req-filterblocks-v2

穿孔のフィラーモデルに列・色の第2候補も含め、その露出率を{rate}とする。
色と紙IDにそれぞれ32層化標本を使う。所有目標の色条件付けと差分キャッシュは保持。
head・第2候補の全ての穴候補を一緒に並べ、係数0.7で一巡する。
通常のheadだけの穿孔を先に行う追加段はなく、区間DPの初期構築も一度にする。
前段の割当・ペア・列と注文処理は基準と同じ。未来の注文は使わない。

d2_trials/viable/acceptedは非head候補の試行・事前評価通過・受理数。
d2_cost_delta/profit_delta/corrected_deltaは非head候補だけの予測変化（手/注文）。
d2_secは混合モデルの構築と一巡の時間。perforation_*は両方を含む全体値。
追加の環境変数はない。既存ログ・@paper/@ops・プロファイラ・予算スイッチ、
CLOCK_SCALE、LOCAL_BENCH、DesignStore、段の目印と目次を保持する。
''')
