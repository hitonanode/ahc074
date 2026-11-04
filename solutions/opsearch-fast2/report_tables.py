"""Rebuild the complete experimental ladder and the selected comparison table from stored results."""
import json
import math
from pathlib import Path
import statistics

folder = Path(__file__).resolve().parent
rows = []
for file in (folder / 'experiments').glob('*.json'):
    d = json.loads(file.read_text())
    a = d['arms'][-1]
    diff = [r['log_percent'][-1] - r['log_percent'][1] for r in d['per_seed']]
    rows.append((d['runs'][0], file.stem, d['seeds'], d['orders'], a['moves'],
                 a['log_percent_mean'], a['log_percent_se'], statistics.mean(diff),
                 statistics.stdev(diff) / math.sqrt(len(diff)),
                 *[v['req_sec_mean'] for v in d['arms']], a['time_ratio']))
text = '| 設定 | run-id接頭辞 | seed×注文列 | 手数 | 対esw log比% ± SE | 対fast log比% ± SE | req_sec esw / fast / fast2 | 対esw倍率 |\n'
text += '|---|---|---|---:|---:|---:|---|---:|\n'
for run, label, n, o, moves, mean, se, diff, dse, base, old, new, ratio in sorted(rows):
    text += f'| {label} | {run.removesuffix("_esw-fixiter")} | {n}×{o} | {moves} | {mean:.6f} ± {se:.6f} | {diff:.6f} ± {dse:.6f} | {base:.6f} / {old:.6f} / {new:.6f} | {ratio:.3f} |\n'
text += '\n接尾辞は `_esw-fixiter` / `_opsearch-fast` / `_opsearch-fast2`。各行の設定と外部負荷は同名 `experiments/*.json`。\n'
text += 'exact-plan-reuseでは両fastにPOST_CANDIDATES=4、exact-pair-ownersとexact-cross-memoでは両fastにNS_TWO=1, NS_ROUNDS=1を指定した。disabledは両fastともNEUTRAL=0。他の行の旧fastは既定値。\n'
text += '各時点の既定値はrunのsrc/main.cppが正本。初期の実験は現在のF2_MODE=0に相当する探索が既定だった。最終推奨値の再現はREADMEのMODEを使う。\n'
(folder / 'ladder.md').write_text(text)
print(f'{len(rows)} comparisons written to ladder.md')
