"""Diagnose the owner credit remaining after 32-stratum sampling."""
from pathlib import Path

root = Path(__file__).resolve().parent.parent
base = root/'argon-des-perf-nonhead32wide-v2'
source = (base/'main.cpp').read_text()
zero = source.replace('static constexpr double secondary_rate = .125;',
                      'static constexpr double secondary_rate = 0.0;')
old = 'if (wide ? (exposure[k] == 0 || k == heads[c][b]) : k != heads[c][b]) continue;'
assert zero.count(old) == 1
zero = zero.replace(old, '''if (wide ? (k == heads[c][b] || std::find(ranked[2*c+b].begin(), ranked[2*c+b].end(), k) == ranked[2*c+b].end())
                     : k != heads[c][b]) continue;''')
old = 'const double correction = last_owner_corrected - last_owner_raw;'
assert source.count(old) == 1
discount = source.replace(old, '''const double correction = (wide ? 0.5 / 0.7 : 1.0) * last_owner_corrected - last_owner_raw;''')
for name, code, description in [
    ('nonheadzero32', zero, '''非headの露出確率を0にする対照。第2候補の穴は探索するが、
区間DPにその紙をフィラーとして出さない。他のheadがその紙の所有目標を修復する
モデル利益だけで穴が選ばれるかを確かめる。headの最初の穿孔は基準どおり。'''),
    ('nonheadowner32', discount, '''非head露出1/8の追加段で、所有目標の利益係数だけを0.7から0.5へ下げる。
donor側は0.7のまま。headの最初の穿孔は0.7のまま。
既存の所有目標の上限は保守的な上限として有効。
d2_corrected_deltaは受理用に所有目標利益を0.5/0.7倍した値、
perf_owner_conditionedは従来どおり倍率を掛ける前の利益。''')]:
    out = root/f'argon-des-perf-{name}'
    out.mkdir()
    (out/'main.cpp').write_text(code)
    (out/'README.md').write_text(f'''改良元: solutions/argon-des-perf-nonhead32wide-v2

{description}

色・紙IDは32層化標本。未来の注文は使わない。
スイッチと指標は改良元と同じ。既存ログ、@paper/@ops、プロファイラ、予算スイッチ、
CLOCK_SCALE、LOCAL_BENCH、DesignStore、段の目印と目次を保持する。
''')
