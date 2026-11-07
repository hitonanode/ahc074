"""Render final report from frozen measurements and validated trial tables."""
from pathlib import Path
import json,sys,re
P=Path(__file__).resolve().parent;root=P.parents[1];name=sys.argv[1];D=root/'solutions'/name
x=json.loads((D/'final-metrics.json').read_text());ids=x['run_ids']['normal'];candidate=next(r for r in ids if r.endswith('_'+name));seven=next(r for r in ids if r.endswith('_deval-seven-wide'));nofb=next(r for r in ids if r.endswith('_deval-vbranch-nofb'));old=ids[0]
f=x['replay']['fresh'];n=x['normal'][candidate];s=(D/'main.cpp').read_text();h=re.search(r'max\(0, remaining\) / (\d+)\.',s);h=int(h[1]) if h else 0
fmt=lambda z:f'{z["mean"]:+.4f} ± {z["se"]:.4f}%'
w=lambda z:'/'.join(map(str,z['wtl']))
passed=n['judge_ratio_old'][0]<=1.10 and n['judge']['p99']<=x['normal'][nofb]['judge']['p99']
t=[f'# Task 4: {name}','',f'未使用seed 500–999の新規注文列1–7で、seven-wide比 **{fmt(f)}**。通常2000件の同時比較のjudgeモデル平均は旧SOTA比 **{n["judge_ratio_old"][0]:.4f}倍**、p99は **{n["judge"]["p99"]:.4f}秒**（nofb **{x["normal"][nofb]["judge"]["p99"]:.4f}秒**）。時間条件は'+('満たした。' if passed else '**満たしていない**。'),'','## 最終解法','', '改良元は`solutions/deval-seven-wide`。窓割当て・焼きなましの探索回数と注文探索の幅を保ち、次の変更を行った。','', '1. 窓割当ての4組の閉包計算で、関係行列の展開を整数表からAVX2 gatherで行う。浮動小数点演算と選ぶ手は同じ。','2. 4つの焼きなまし分岐の後、通常の再仕上げと穴を保存する再仕上げを交互に2回ずつ行い、V16で全8候補から選ぶ。各回は現在の最良完成配置から始める。通常の追加仕上げはclimb25k＋再割当て1回＋穴あけ＋最終再割当て。穴保存ではclimbと前半の再割当てを省き、既存の穴から穴あけと最終再割当てを行う。自然な紙の模様を復元元として保持し、穴の復元も物理紙へ正しく反映する。','3. 最終設計の各列内で、同じ色の紙を既存のfiller需要込みの重み順にし、2色の混ぜ方を小さいDPで選ぶ。目的は `Σ w_k × depth_k / 256 + h_0 × first_0 + h_1 × first_1`。紙の番号とdedを対応して更新する。模様、担当注文、所属列は変わらない。注文列は使わない。']
if 'if(std::strcmp(name,"PLAN_SHORTLIST")==0)return "3";' in s:t.append('4. 注文後処理で、採用案と同じ手数の別計画も再検討する固定設定PLAN_SHORTLIST=3を使う。')
if h:t.append(f'4. 最後の{h}注文は、将来返却費用と次状態価値を `min(1, 残り注文数/{h})` 倍する。最終注文では将来費用を0にする。探索予算は固定で、既知の注文残数だけを使う。')
t+=['', '初期順序の簡易DPは約0.48 ms。列MDPで初期状態を選ぶ案と品質差がなく、後者には約9.60 msかかった。通常500件では改善のほぼ全てが最初の256注文にあり、その後768注文の差は−0.014 ± 0.141手だった。紙を印刷する時点なら列内の並べ替えに操作を払わずに済むため、望ましい順番へ近づくまでの手数を減らせる。', '', '穴保存の2候補は学習用500件の59%で選ばれた。8候補版の仕上げ時間は約0.205秒で、seven-wideの7候補とほぼ同じ。追加のVと初期順序の計算を、窓割当ての高速化で賄う。','', '全て固定seed・固定回数。時間不足による軽量モード、設計時間上限、時刻による候補数変更はない。DesignStoreは初期順序を整えた最終設計を保存する。@paper/@opsと段の目印・目次を維持した。','', '## 評価方法','', '設定選択はseed 0–499のみ。学習基準は`20261107-113720_deval-seven-wide`（保存設計111153の8列再評価）。第一候補ordered8-plan3と比較用ordered8を固定し、同じ通常2000件比較に入れた。事前にfreeze.jsonへ記した優先順に、平均時間とp99の制約だけで採用を確定し、未使用500–999の新規列は選択に使わず最後に一案を評価した。新規7列の基準は`20261107-112011_deval-seven-wide`。差はseedごとに対象列の平均スコアを取り、そのlog比×100をseed間で平均した。負が改善、±は標準誤差。元の注文列も別に報告する。','', '`judge = 1.04 × helper_end_sec + 1.35 × req_sec + (end_sec − helper_end_sec − req_sec)`。全時間比較は24並列の同時比較。ビルドと重い分析は共有flockの下で行った。','', '## 通常2000件の最終比較','', '| 解法 | 平均スコア | judge平均 秒 | old比 | judge p99 秒 | judge最大 秒 |','|---|---:|---:|---:|---:|---:|']
for r in ids:
 z=x['normal'][r];t.append(f'| {r.split("_",1)[1]} | {z["score_mean"]:.3f} | {z["judge"]["mean"]:.6f} | {z["judge_ratio_old"][0]:.5f} | {z["judge"]["p99"]:.6f} | {z["judge"]["max"]:.6f} |')
t+=['','ordered8-plan3はp99がnofbを約6.6 ms上回ったため不採用。ordered8のp99の余裕は約4.0 ms。judgeモデルの最大は2.0335秒、2.0秒超えは2/2000件であり、時間不足の切り替えは指定どおり設けていない。','','| 最終版の比較基準 | 差 ± SE | 勝/分/敗 |','|---|---:|---:|']
for ref in [old,seven,nofb]:
 z=x['paired_scores'][candidate+' vs '+ref];t.append(f'| {ref.split("_",1)[1]} | {fmt(z)} | {w(z)} |')
t+=['','run: '+', '.join('`'+r+'`' for r in ids)+'. 最終通常比較は`--no-record`を付けず記録した。','', '| 解法 | end_sec平均 | p99 | 最大 | >1.8 / >1.9 / >2.0秒 | 外部負荷 平均/最大core |','|---|---:|---:|---:|---:|---:|']
for r in ids:
 z=x['normal'][r];e=z['end_sec'];o=z['outside_load'];t.append(f'| {r.split("_",1)[1]} | {e["mean"]:.6f} | {e["p99"]:.6f} | {e["max"]:.6f} | {e["over_1_8"]}/{e["over_1_9"]}/{e["over_2"]} | {o["mean_cores"]:.3f}/{o["max_cores"]:.3f} |')
t+=['','| 段 | seven-wide 平均秒 | 最終版 平均秒 | 差 ± SE 秒 |','|---|---:|---:|---:|']
for key,label in [('map_end_sec','窓割当てまで'),('dv_anneal_sec','焼きなまし'),('dv_finish_sec','仕上げ'),('dv_eval_sec','V'),('helper_end_sec','設計・補助表の合計'),('req_sec','注文')]:
 values=x['stage_deltas_vs_seven'][key];t.append(f'| {label} | {x["normal"][seven]["stage_mean"][key]:.6f} | {n["stage_mean"][key]:.6f} | {values[0]:+.6f} ± {values[1]:.6f} |')
t+=['','## 凍結ソースの8列再評価','',f'候補 `{x["run_ids"]["replay"]}`、基準 `{x["run_ids"]["reference"]}`。500ケース。','', '| 注文列 | 差 ± SE | moves/order差 | 勝/分/敗 |','|---|---:|---:|---:|']
for k,label in [('fresh','新規1–7'),('all','全8列'),('real','元の列0')]:
 z=x['replay'][k];t.append(f'| {label} | {fmt(z)} | {z["moves_per_order"]:+.6f} | {w(z)} |')
t+=['','## 検証と再現','',f'最終main.cppは **{x["audit"]["source_bytes"]:,} bytes**（上限520,000）。凍結時SHA256は`{x["audit"]["sha256"]}`。通常runとreplayのソースは一致。通常実行と再読込の列0のstdoutは500/500件で一致した。全4000リプレイで不正表示と操作ラベル不整合は0。詳細は`final-metrics.json`、提出用GCC/ClangのC++23ビルド結果は`builds.json`（通常-O2）と`builds-native.json`（-march=native）。','', '窓gatherはGCC・Clangの各250件でstdoutが全件一致した。段の時間差はGCC −9.80 ± 2.35 ms、Clang −12.43 ± 2.15 ms。初期順序については500設計全件で列ごとの紙模様の集合と各注文の担当紙模様が保存されることも照合した。','', '実験スクリプトは`../deval-next/`に置いた。`run.py`は標準`scripts/pahcer_run.py`を呼び、ビルドにもflockを付ける。同一ソース・コンパイラ・フラグの完了binaryだけ再利用する。`make_*.py`と`combine.py`が各候補を生成し、`experiments.jsonl`が設計runとreplayを対応付ける。`summarize.py`、`analyze_quality.py`、`final_metrics.py`で再集計できる。','', '```sh','PYTHONDONTWRITEBYTECODE=1 /home/sato/ahc074/.venv/bin/python solutions/deval-next/run.py --compare '+' '.join('solutions/'+r.split('_',1)[1] for r in ids)+' --seeds 0-2000 --save-design -c "Task4 frozen final"',f'PYTHONDONTWRITEBYTECODE=1 /home/sato/ahc074/.venv/bin/python solutions/deval-next/run.py solutions/{name} --design-from {candidate} --orders 8 --seeds 500-1000 -c "Task4 frozen test"','```','', '## 全試行','', '以下は学習用試行。最終採否は上の凍結評価を優先する。stage差はlocal scaled時間。固定設計replayの注文時間差は列0のstderrをseed間で集計した。','']
t.append((P/'EXPERIMENTS.md').read_text().replace('# Task 4 学習用試行一覧','### 学習用試行一覧',1).replace('\n## ','\n### '))
(D/'REPORT.md').write_text('\n'.join(t)+'\n')
print(D/'REPORT.md')
