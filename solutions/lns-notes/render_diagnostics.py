"""Render validated candidate diagnostics; does not run or fit a solver."""
from pathlib import Path
import json

h=Path(__file__).resolve().parent
datasets={name:json.loads((h/f'diagnostic-{name}-fixed-metrics.json').read_text())
          for name in ['star','joint']}
lines=['# 完成候補とVの診断', '',
       '全て訓練seed 0–99の保存候補をhelper-wideで8列再生したもの。修正済み `*-fixed` の正のスコアだけを使用した。各修復の候補は3回の仕上げからVで選んだもの。', '',
       '相関はseed内で中心化したpooled Pearson。回帰傾きは、同じ中心化後の実コストをVに回帰した値。新規6列（1–6）の補正は1–3と4–6のsplit-half相関にSpearman–Brown補正を施して行う。有限標本の推定なので補正後の値は丸めて1へ切り詰めない。', '',
       '| 方式 | 候補群 | seed数 | r（新規1–7） | r（新規1–6） | 補正r（1–6） | r（全8） | 補正r（全8） | 全8での回帰傾き |',
       '|---|---|---:|---:|---:|---:|---:|---:|---:|']
labels={'branches':'既存4分岐','lns_finished':'修復後の4候補','lns_with_base':'元の最良＋4修復'}
def num(x): return '—' if x is None else f'{x:.3f}'
def stat(x): return f'{x["mean"]:+.5f} ±{x["se"]:.5f}'
for name,d in datasets.items():
    assert d['all_trace_moves_equal_scores']
    for group,label in labels.items():
        g=d['groups'][group];f=g['fresh_lists1_6']
        lines.append(f'| {name} | {label} | {g["n_cases"]} | {num(g["fresh_lists1_7_r"])} | {num(f["r"])} | {num(f["corrected_r"])} | {num(g["r"])} | {num(g["corrected_r"])} | {g["within_case_slope"]:.3f} |')
for name,d in datasets.items():
    failed=sum(v for k,v in d['failed_repair_exports'].items() if 2000<=int(k)<2010)
    lines.append(f'\n{name}: 400修復枠のうち{failed}枠は修復失敗で親を残した。相関と選択の表では、この実際の候補枠を親の複製として含めている。')
lines+=['','## 校正','','単位は手/注文。平均差はV−全8列の実コスト、RMSEはseed内中心化後のV−実測値。差の符号が負ならVが実コストを低く見積もる。','','| 方式 | 候補群 | 平均差 | 中心化後RMSE |','|---|---|---:|---:|']
for name,d in datasets.items():
    for group,label in labels.items():
        g=d['groups'][group]
        lines.append(f'| {name} | {label} | {g["absolute_bias_V_minus_real"]:+.5f} | {g["centered_rmse"]:.5f} |')
lines+=['','## 競合する候補だけの精度','','元の最良設計のVから+0.05手/注文以内で、同一seedに2候補以上ある部分集合（全8列）。Vだけで部分集合を定義しており、実コストでは絞っていない。','','| 方式 | seed数 | 候補数 | r | 補正r | 傾き |','|---|---:|---:|---:|---:|---:|']
for name,d in datasets.items():
    g=d['groups']['lns_with_base'].get('competitive_within_005_V')
    if g: lines.append(f'| {name} | {g["n_cases"]} | {g["n_entries"]} | {num(g["r"])} | {num(g["corrected_r"])} | {g["slope"]:.3f} |')
lines+=['','## 選択の実コスト','','元の最良＋最初の4修復から選び、lists4–7で測定。差は選択後−元の最良、単位は手/注文。4列選択器はlists0–3で選ぶ雑音を持つ対照であり、完全oracleではない。','','| 方式 | Vで選択 | 4列で選択 |','|---|---:|---:|']
for name,d in datasets.items():
    g=d['groups']['lns_with_base']
    lines.append(f'| {name} | {stat(g["V_pick_vs_base_lists4_7"])} | {stat(g["oracle_vs_base_lists4_7"])} |')
lines+=['','## 第1修復の仕上げ前後','','同一親に対する子の差を新規lists1–7で測定。子の仕上げ前は列anneal後。親の未仕上げ参照は、完成時の割当から追加穿孔なしで再印刷した状態であり、履歴上のclimb/rematch前を復元したものではない。初期紙順も再構成するため、finishing単独の因果効果ではなく構造診断として読む。','','| 方式 | 成功修復数 | 仕上げ前の実手数差 | 前の改善率 | 完成後の実手数差 | 後の改善率 |','|---|---:|---:|---:|---:|---:|']
for name,d in datasets.items():
    for j,g in d['finishing'].items():
        f=g['successful_repairs_only']
        lines.append(f'| {name} / step {j} | {f["n"]} | {stat(f["before_delta"])} | {100*f["before_better_fraction"]:.1f}% | {stat(f["after_delta"])} | {100*f["after_better_fraction"]:.1f}% |')
lines+=['','starは完成候補のみを保存したため、仕上げ前後の対応比較はjointで行った。失敗修復は親を複製して明示的に記録し、上表の成功修復数から除いている。','','## 検査と出典','']
lines+=['外部負荷警告が出た候補再生は同じ設計・注文列で再実行し、全800出力とスコアの一致を検査する。確認記録は `clean-candidate-checks.json`、run対応はREPORT.mdを参照。','']
for name,d in datasets.items():
    lines.append(f'- {name}: {d["trace_verified_requests"]:,}注文で操作ラベル総数＝得点、表示誤り・計画失敗のカウンタ0を照合。詳細 `diagnostic-{name}-fixed-metrics.json`。')
    ids=', '.join(f'{cid}: `{row["replay"]}`' for cid,row in d['sources'].items())
    lines.append(f'- {name} の候補IDと再生run: {ids}。')
(h/'DIAGNOSTICS.md').write_text('\n'.join(lines)+'\n')
print('\n'.join(lines))
