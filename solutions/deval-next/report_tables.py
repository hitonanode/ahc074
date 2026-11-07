"""Write Japanese tables from validated completed experiment summaries."""
from pathlib import Path
import json
P=Path(__file__).resolve().parent
rows=json.loads((P/'summary.json').read_text())
fmt=lambda x:f'{x[0]:+.4f} ± {x[1]:.4f}'
ms=lambda x:f'{1000*x[0]:+.2f} ± {1000*x[1]:.2f}'
s=['# Task 4 学習用試行一覧','', '設定選択はseed 0–499のみ。差は候補−seven-wide、負が改善。±はseed単位の標準誤差。注文列の平均スコアのlog比を%で示す。通常評価とreplayは分けて時間を読む。','', '## 出力同一の高速化','', '各250ケース、24並列の同時比較。出力一致はstdoutファイルをバイト単位で照合。全候補数は固定。†は外部CPU負荷の警告があるため、時間差の採否に使わない。','', '| 解法 | 段 | 段の時間差 ms ± SE | 出力一致 | 候補run |','|---|---|---:|---:|---|']
for r in rows:
 if r['kind']!='speed':continue
 run=r['run'];name=run.split('_',1)[1];k='map_end_sec' if 'map-' in name else 'dv_eval_sec' if name in ['deval-vintdp','deval-vskipdp','deval-vcapacity'] else 'dv_finish_sec' if 'perf-copy' in name else 'req_sec'
 label={'map_end_sec':'窓割当て','dv_eval_sec':'V','dv_finish_sec':'仕上げ','req_sec':'注文'}[k]
 if run.startswith('20261107-121916'):name+=' Clang'
 
 if r.get('outside_load',{}).get('mean_cores',0)>.5 or r.get('outside_load',{}).get('max_cores',0)>3:name+=' †'
 s.append(f'| {name} | {label} | {ms(r[k])} | {r["identical"]}/{r["n"]} | `{run}` |')
s+=['','## 設計の変更','', '全て500ケース×8列。学習基準replayは`20261107-113720_deval-seven-wide`。時間は各案の同時通常比較。judge比の分母は同時比較のargon、p99は候補/nofbの秒。','', '| 解法 | 列1–7 % ± SE | 全8列 % ± SE | 元の列 % ± SE | 設計時間差 ms ± SE | judge比 | p99 候補 / nofb | 設計run / replay |','|---|---:|---:|---:|---:|---:|---:|---|']
for r in rows:
 if r['kind']!='quality':continue
 s.append(f'| {r["tag"]} | {fmt(r["fresh"])} | {fmt(r["all"])} | {fmt(r["real"])} | {ms(r["design_delta"])} | {r["judge_ratio_old"]:.4f} | {r["judge_p99"][0]:.4f} / {r["judge_p99"][1]:.4f} | `{r["design"]}` / `{r["run"]}` |')
s+=['','`warm9/7/10`と`latemix10`は、穴を復元すると判断した箇所が物理紙に反映されない初期試験版を含む。出力は合法だが意図した処理と異なるため、採用候補と区別する。`warmfix*`は自然な紙を復元元として保持する修正版、`warmadd9`は既存の穴を固定して追加だけ試す版。','','## 注文処理だけの変更','', '500ケース×4列、保存設計`20261107-111153_deval-seven-wide`。同時比較。時間はreplay同士のreq_sec差であり、通常実行のjudge比には使わない。','', '| 解法 | 全4列 % ± SE | 列1–3 % ± SE | 元の列 % ± SE | 注文時間差 ms ± SE | run |','|---|---:|---:|---:|---:|---|']
for r in rows:
 if r['kind']!='request':continue
 s.append(f'| {r["run"].split("_",1)[1]} | {fmt(r["all4"])} | {fmt(r["fresh3"])} | {fmt(r["real"])} | {ms(r["req_delta"])} | `{r["run"]}` |')
(P/'EXPERIMENTS.md').write_text('\n'.join(s)+'\n')
