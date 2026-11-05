"""Summarize completed D2 comparisons; run under whenidle.sh and the evaluation lock."""
import json
from pathlib import Path

here = Path(__file__).resolve().parent
sources = [
    ('第2候補 1/8', 'compare-500.json'),
    ('露出率と第3候補', 'rates-500.json'),
    ('64標本（負荷警告のない再測定）', 'dense-clean-500.json'),
    ('紙の組合せの全列挙', 'exactmix-500.json'),
    ('同時2穴・時間超過の測定版', 'pairs-100.json'),
    ('前段の混合目的', 'headmix-2000.json'),
    ('自目標とdonorの寄与分離', 'audit-500.json'),
    ('色で条件付け・新基準', 'condition-v2-summary.json'),
    ('旧状態側のDP再利用', 'final-fast-2000.json'),
    ('厳密上限による棄却・最終', 'bound-2000.json'),
]
lines = ['# D2の比較結果と時間', '',
         '差は各比較の先頭を基準とする平均logスコア比。負が改善、±は標準誤差。',
         '時間は秒。judge = end_sec + 0.04 × helper_end_sec + 0.35 × req_sec。',
         '通常比較は記録済み。同時2穴だけは時間超過の測定版として `--no-record`。',
         '各比較の基準も載せ、異なる実行間の時間差では採否を決めない。', '']
for title, file in sources:
    rows = json.loads((here / file).read_text())
    lines += ['## ' + title, '',
              '| run-id | 件数 | 差 ± SE (%) | 勝/分/敗 | req | helper end | end | judge平均 | p99 | 最大 | >2秒 |',
              '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in rows:
        m, j, s = r['metrics'], r['judge'], r['score']
        times = [m[k]['mean'] for k in ('req_sec', 'helper_end_sec', 'end_sec')]
        times += [j['mean'], j['p99'], j['max']]
        lines.append('| ' + r['run'] + ' | ' + str(r['n']) +
                     f" | {s['mean']:+.6f} ± {s['se']:.6f} | " + '/'.join(map(str, r['wtl'])) +
                     ' | ' + ' | '.join(f'{v:.6f}' for v in times) + f" | {j['over2']} |")
        assert r['wa'] == 0
        for k in ('self_wrong', 'op_label_errors'):
            assert m[k]['max'] == 0
    lines += ['']
lines += ['全表の全ケースでWA、self_wrong、op_label_errorsは0。',
          '元データは各表に対応する同ディレクトリのJSON。', '']
(here / 'MEASUREMENTS.md').write_text('\n'.join(lines))
print('Wrote MEASUREMENTS.md')
