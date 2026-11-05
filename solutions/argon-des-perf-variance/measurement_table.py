"""Read completed summary JSON files; launch via whenidle.sh."""
import json
from pathlib import Path

here = Path(__file__).resolve().parent
sources = [
    ('標本分散と係数0.4/0.6', 'first-500.json'),
    ('512標本・時間超過の測定専用版（記録なし）', 'oracle-500.json'),
    ('donor価格の条件付け', 'donorprice-500.json'),
    ('係数0.7/0.8/1.0の探索比較（外部負荷警告あり・採否に使わない）', 'weights-500.json'),
    ('係数0.7のみ・2000件（p99が時間枠外）', 'gain70-final2000.json'),
    ('係数0.7のみ・時間の再確認（候補p99が時間枠外）', 'gain70-timecheck2000.json'),
    ('不変DP行の再利用・500件', 'gaincache-500.json'),
    ('不変DP行の再利用・最終2000件', 'gaincache-2000.json'),
]
lines = ['# D2 続き: 全比較の得点と時間', '',
         '差は各表の先頭を基準とする平均logスコア比。負が改善、±は標準誤差。',
         '時間は秒。judge = end_sec + 0.04 × helper_end_sec + 0.35 × req_sec。',
         '512標本だけは時間超過の測定として記録せず、他の通常比較は記録した。', '']
for title, file in sources:
    lines += ['## ' + title, '',
              '| run-id | 件数 | 差 ± SE (%) | 勝/分/敗 | req | helper end | end | judge平均 | p99 | 最大 | >2秒 |',
              '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in json.loads((here / file).read_text()):
        m, j, s = r['metrics'], r['judge'], r['score']
        times = [m[k]['mean'] for k in ('req_sec', 'helper_end_sec', 'end_sec')]
        times += [j['mean'], j['p99'], j['max']]
        lines.append('| ' + r['run'] + ' | ' + str(r['n']) +
                     f" | {s['mean']:+.6f} ± {s['se']:.6f} | " + '/'.join(map(str, r['wtl'])) +
                     ' | ' + ' | '.join(f'{v:.6f}' for v in times) + f" | {j['over2']} |")
        assert r['wa'] == 0
        assert all(m[k]['max'] == 0 for k in ('self_wrong', 'op_label_errors'))
    lines += ['']
lines += ['全てWA・self_wrong・op_label_errorsは0。元データは同ディレクトリのJSON。', '']
(here / 'MEASUREMENTS.md').write_text('\n'.join(lines))
print('Wrote MEASUREMENTS.md')
