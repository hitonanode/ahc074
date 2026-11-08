"""Render the measured pilot table, without rerunning any solver or statistics."""
from pathlib import Path
import json

h=Path(__file__).resolve().parent
rows=json.loads((h/'pilot-consolidated.json').read_text())
lines=['# 訓練側の全予備測定', '',
       'seed 0–99、helper-wide の注文処理で8列再生。以下は新規lists 1–7。差は候補−基準（負が改善）、±はseed間の標準誤差。%は各seedの7列のlog比を平均してからseed間で平均する。基準再生は `20261108-040819_deval-helper-wide`。設定は各解法のconfig.jsonと評価時のsrc/main.cppを参照。', '',
       '設計秒は24並列の通常同時比較のhelper_end_sec。異なるrun間の時間の小差を採否には使わない。各研究版は固定予算で、通常評価は --no-record。負荷欄は平均0.5コアまたは最大3コアを超えたrunを示し、その時間の小差を根拠にしない。主方式と対照は、負荷の低い凍結比較で再確認する。', '',
       '| 解法 | 手/注文 ±SE | % ±SE | 設計秒（基準比） | 設計run | 再生run | 負荷警告 |',
       '|---|---:|---:|---:|---|---|---|']
for x in rows:
    d=x['replay']['score']['fresh'];t=x['normal']['stage']['helper_end_sec']
    if 'replay_run' not in x:
        table=json.loads((h/(x['tag']+'.json')).read_text())
        x['replay_run']=next(y['replay'] for y in table if Path(y['source']).name==x['source'])
    pc=d.get('pct_orders',d['pct']);ps=d.get('pct_orders_se',d['pct_se'])
    warnings=[]
    for key,label in [('normal','通常'),('replay','再生')]:
        load=x[key].get('outside_load') or {}
        if load.get('mean_cores',0)>.5 or load.get('max_cores',0)>3:warnings.append(label)
    warn='・'.join(warnings) or 'なし'
    lines.append(f'| {x["source"].split("_",1)[1]} | {d["moves"]:+.5f} ±{d["moves_se"]:.5f} | {pc:+.4f} ±{ps:.4f} | {t["mean"]:.3f}（{t.get("ratio",float("nan")):.2f}×） | `{x["source"]}` | `{x["replay_run"]}` | {warn} |')
lines += ['', '## 破壊と修復の診断', '',
          '以下は成功した修復ステップの平均。修復失敗数・全試行の値は pilot-consolidated.json に別記した。window_changes のない古い試作は未計測。完成V改善率は親に対する率。controlのダミー欄は載せない。', '',
          '| 解法・設計run時刻 | 旧ペア破壊 | 修復商品 | 完成後新ペア | 変更窓 | 完成V改善率 |',
          '|---|---:|---:|---:|---:|---:|']
for x in rows:
    d=x['normal'].get('diag',{})
    if d.get('mode') not in [1,6]:continue
    w=d.get('window_changes');ws=f'{w:.2f}' if w is not None else '—'
    lines.append(f'| {x["source"]} | {d["destroyed"]:.2f} | {d["free_targets"]:.2f} | {d["new_finish"]:.2f} | {ws} | {100*d["better"]:.2f}% |')
(h/'TRAINING.md').write_text('\n'.join(lines)+'\n')
(h/'pilot-consolidated.json').write_text(json.dumps(rows,indent=2)+'\n')
