"""Render frozen final metrics and benchmark results; never changes a model."""
import os
os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
import sys
sys.dont_write_bytecode=True
from pathlib import Path
import json
import numpy as np
HERE=Path(__file__).resolve().parent
r=json.loads((HERE/'TEST_RESULTS.json').read_text())
chosen=r['selected_model'];best=r['models'][chosen]['all'];base=r['models']['model_cost']['all']
spec=json.loads((HERE/'models'/(chosen+'.final.json')).read_text())
bench=json.loads((HERE/'value_benchmark.json').read_text())
gcc=[x['milliseconds'] for x in bench if x['compiler']=='g++']
clang=[x['milliseconds'] for x in bench if x['compiler']=='clang++']
init=[x['init_milliseconds'] for x in bench if x['compiler']=='g++']
maxerr=max(abs(x['error']) for x in bench)
labels={
 'model_cost':'model_cost','model_col':'model_col','model_hole':'model_hole','model_gc':'model_gc',
 'd2_model_final':'d2_model_final','baseline_calibrated':'従来項を再校正（参考）',
 'analytic_minimal':'列ごとの解析式（7項）','static_all':'列・対象の静的集計',
 'head_analytic':'先頭filler価値を追加','coupled_small':'被覆DP 128点・1設定',
 'filler_all':'被覆DP 128点・12設定','fast_all':'被覆DP 32点・1設定',
 'compact_all':'被覆DP 32点・2設定','markov_all':'色分布更新 128点・全設定（重い参考）',
 'stationary_all':'色分布更新 16点・4回','stationary32_all':'**採用 V：32点・更新2回**',
 'persistent_all':'残置確率で返却費用を補正','target_fast':'注文別の木モデル＋校正'}
order=['model_cost','model_col','model_hole','model_gc','d2_model_final','baseline_calibrated',
       'analytic_minimal','static_all','head_analytic','coupled_small','filler_all','fast_all',
       'compact_all','markov_all','stationary_all','stationary32_all','target_fast','persistent_all']

def delta(m,k):
    v,se=m[k];pct=m[k+'_pct'][0]
    return f'{v:+.5f} ± {se:.5f} ({pct:+.3f}%)'

text=f'''# 設計だけから平均操作数を予測する評価関数

**採用は、列の先頭色を2回更新する32点の被覆モデル V。** 未使用の test seed 500–999（500ケース、各7設計、共通8注文列）で、ケース内相関は **{best['r']:.4f}**、測定ノイズの補正後は **{best['r_corrected']:.4f}**。`model_cost` は **{base['r']:.4f} / {base['r_corrected']:.4f}** だった。

Vで設計を選ぶと、baseに対して **{delta(best,'base')} 操作／注文**、一様ランダム選択に対して **{delta(best,'random')} 操作／注文**。C++の完全な評価は手元のGCCで中央値 **{np.median(gcc):.3f} ms**、既知の1.35倍を使ったジャッジ時間の目安は **{1.35*np.median(gcc):.3f} ms**。以下、差は「選択 − 比較先」で、負が改善。±はケースを単位とした標準誤差であり、95%信頼区間ではない。

## 分割とデータ

- 学習・選択：seed 0–399で学習し、400–499で設定・正則化を選んだ。下のモデルは全7設計が揃った状態で同じ分割で検証した。
- 最終学習：seed 0–499で再学習。test 500–999はモデルと設定を `FROZEN.json` に固定した後に評価した。テストに基づく設定変更、切片・傾きの補正はしていない。
- 各ケースはbase、全体再始動3個、焼きなまし以降だけの再始動3個。各設計の実測は共通の8注文列の平均。全7000設計・56000注文列について、全操作ラベルの合計がスコアと一致し、不一致注文の罰点を含まないことを検査した。
- 予測側の特徴は、最終の `DesignState` とバーコードだけから計算する。実測のラベルや注文列は教師としてだけ読む。`Solver::process`、紙の重なりの模擬、操作列の生成は行わない。
- 全体再始動の比較集合はbase＋3個、焼きなましのみの比較集合もbase＋その3個。一様ランダム選択は、それぞれの集合内でbaseも含めた期待値である。

## テストの指標

相関は、予測と8列平均の実測を各ケース内で中心化してからプールしたPearson相関。前半4列と後半4列を同じ方法で中心化した相関を h とし、信頼性を `ρ=2h/(1+h)`、補正相関を `r/√ρ` とした。百分率の差はケースごとの比の平均である。

| 設計集合 | ケース数 | 設計数／ケース | split-half相関 | 8列平均の信頼性 |
|---|---:|---:|---:|---:|
'''
group_names={'all':'全7設計','full':'全体再始動','anneal':'焼きなましのみ'}
for g,gn in group_names.items():
    m=r['models'][chosen][g]
    text+=f"| {gn} | {m['n']} | {m['designs']} | {m['half_correlation']:.4f} | {m['reliability']:.4f} |\n"
text+='\n採用Vの全7設計での相関のケースbootstrap標準誤差は '+f"{best['r_bootstrap_se']:.4f}"+'、95%区間は '+f"[{best['r_bootstrap_ci95'][0]:.4f}, {best['r_bootstrap_ci95'][1]:.4f}]"+'。以下の表は、試した各モデルを固定したままテストで評価したもの。モデル選択は上記の検証分割で完了している。\n'
for g,gn in group_names.items():
    text+=f'\n### {gn}\n\n| モデル | 相関 | 補正相関 | 対base：操作／注文（%） | 対ランダム：操作／注文（%） |\n|---|---:|---:|---:|---:|\n'
    for n in order:
        m=r['models'][n][g]
        text+=f"| {labels[n]} | {m['r']:.4f} | {m['r_corrected']:.4f} | {delta(m,'base')} | {delta(m,'random')} |\n"
text+='''
`model_cost` とその3部分は穴あけ前のstderrの値、`d2_model_final` は最後の再割り当て後の値。「従来項を再校正」はこの5項と `d2_filler_final` を用いた参考モデルで、過去段階の値を含むため、最終状態だけのVの候補にはしていない。他の解析式・被覆・色分布更新のモデルは物理的な最終状態から再計算した。

### 前半で選び、後半で測るoracleとの比較

Vとmodel_costは注文列を見ずに選び、下表では注文列4–7だけで測る。oracleは列0–3の実測平均で選び、列4–7で測る。これは指定された比較であり、有限4列の選択自体にノイズがあるので、真の期待値を知るoracleの厳密な上限ではない。

| 設計集合 | 選択方法 | 後半4列・対base：操作／注文（%） | 後半4列・対ランダム：操作／注文（%） |
|---|---|---:|---:|
'''
for g,gn in group_names.items():
    for n in [chosen,'model_cost']:
        m=r['models'][n][g]
        text+=f"| {gn} | {'V' if n==chosen else n} | {delta(m,'base_half')} | {delta(m,'random_half')} |\n"
    m=r['models'][chosen][g]
    text+=f"| {gn} | oracle（前半4列で選択） | {delta(m,'oracle_base')} | {delta(m,'oracle_random')} |\n"

text+='''
## 何が効いたか、どこで探索を止めたか

従来の取っ手項は、fillerを使わない場合の誤色要求の集計に近い。要求色の偏りだけでなく、対象ごとに「何が覆われ、どの色直しが残るか」を評価する必要があった。さらに、fillerが現在の先頭色を見て選ばれるため、残る要求の色比だけでは次の先頭色の分布を表せない。残る色直しの条件付き遷移率で分布を更新すると、設計間の順位付けが改善した。

検証seed 400–499、全7設計の結果は次の通り。数値はテストの結果ではない。

| 検討 | 検証相関 | 判断 |
|---|---:|---|
'''
decisions={'head_analytic':'従来項へのfiller価値の追加が有効','filler_all':'対象ごとの被覆の競合を入れて改善',
           'markov_all':'色分布を更新してさらに改善','stationary32_all':'時間を満たす採用形',
           'target_fast':'注文別の木モデルは改善しない','persistent_all':'残置確率の補正による改善は0.02未満'}
for n in decisions:
    v=r['frozen']['validation'][n]['metrics']['all']['r']
    text+=f"| {labels[n]} | {v:.4f} | {decisions[n]} |\n"
text+='''
色分布更新の後に試した「注文別の木モデル」と「残置確率による返却費用の補正」が、どちらも検証相関を0.02以上高めなかった。指定の早期停止条件に従い、新しい予測方式の探索を止めた。計算点数・設定数の削減は同じモデルの時間と精度の比較であり、テストに戻って選び直してはいない。

木モデルは、注文対象ごとの実測を、取っ手関連（fix+fill+fdig+fret+relevel+reuse）、汎用紙（gen+help+hdig）、列と往復（dig+lift+ret）、後処理（repair）に分けて学習した。設計レベルの校正にはseedを分離した2分割の予測を使った。色直しだけを当てて他の操作への置き換えを見落とす比較にはしていない。それでも、細かい設計差の予測では今回の解析的な代理モデルの方がよかった。

## 最終Vと校正

完全な式・全特徴の定義は [SPEC.md](SPEC.md)、そのまま呼べるC++23コードは [value.hpp](value.hpp)。その係数を含む、自己完結した移植用の生成物はディレクトリ内のヘッダー群である。

1. 列の紙数、対象数、取っ手の色要求と汎用紙の半順序を集計する。
2. 各列・色で、対象頻度と静的なfiller価値から代表紙を選ぶ。
3. 固定32点で先頭色の分布を積分する。各対象で誤色の取っ手を被覆する区間DPを解き、残るfixとfill・digなどを集計する。
4. 残った色直しから列の先頭色の条件付き遷移率を更新し、2回繰り返す。
5. これらの特徴と列・汎用紙・穴の集計の線形結合を返す。切片も含めて単位は操作／注文。

'''
text+=f"主な固定値は、リセット強度2、分布更新の減衰0.5、fillerの代理費用1.6、逆色代表の掘り出し費用1、Sobol seed 19790427。最終のridge係数は `{chosen}.final.json`、特徴数は{len(spec['feature_names'])}、正則化係数は{spec['alpha']:g}。\n\n"
text+=f"テストの平均実測コストは {best['mean_cost']:.5f} 操作／注文。Vの平均バイアスは {best['calibration_bias']:+.5f}、RMSEは {best['rmse']:.5f}。ケース内中心化後のRMSEは {best['within_rmse']:.5f}、予測に対する実測のケース内回帰の傾きは {best['calibration_slope']:.4f}。全体の単位と変動幅を実操作数に合わせてある。共線性があるため、各係数を独立した実操作の単価として使うのではなく、V全体として使う。\n\n"
text+=f'''## 計算量とC++確認

- 列・要求の集計はO(PH+K)、代表紙の価値は概ねO(PKH)、被覆DPはO(P×S×H×区間長)。採用形はS=32で3回の積分。対象ごとに点列を内側で回し、donorの区間をキャッシュに残す。
- GCC `-std=c++23 -O2 -march=native` の実測中央値 {np.median(gcc):.3f} ms、最小 {min(gcc):.3f}、最大 {max(gcc):.3f}。ジャッジ換算の目安は中央値 {1.35*np.median(gcc):.3f} ms。生の手元時間であり、CLOCK_SCALEを二重には掛けていない。
- 設計非依存の汎用紙の表の初期化は別に中央値 {np.median(init):.3f} ms。候補ごとには作らず共有する。既存の汎用紙の表と共有する余地もある。
- ClangでもC++23でビルドし、中央値 {np.median(clang):.3f} ms。両コンパイラの予測とPythonで保存した予測の最大差は {maxerr:.3g} 操作／注文。予測の実装確認には訓練範囲のseedだけを使った。
- 詳細な実測は `value_benchmark.json`。低速な全設定のモデルは精度の参考であり、5 ms程度の候補評価としては採用していない。

## 統合の提案

**まず候補選択にVを使う。** 全Vを焼きなましの各近傍に入れるのは重い。候補が4個なら評価そのものは手元で約{4*np.median(gcc):.1f} msで済む。新たな候補を作る費用の方が大きいので、次の順で検討する。

1. 焼きなまし中のelite状態を少数保存し、それぞれをfiller climb、再割り当て、穴あけ、最後の再割り当てまで仕上げてVで選ぶ。これなら窓割り当てと焼きなましを丸ごと繰り返す必要がない。ただし今回のデータは独立な再始動で、同じ軌跡のelite同士の選択益は別に測る必要がある。
2. 焼きなまし以降だけの再始動。窓割り当て・比較器・goptを共有できる。上の「焼きなましのみ」のテスト結果が、この候補集合について直接の証拠になる。ただし再始動ごとの設計時間自体は必要。
3. 全体再始動。上の表で選択益は確認できたが、窓割り当てからやり直すため、2秒枠での候補生成には最も高い費用がかかる。

焼きなましに増分更新で入れられるのは、列コスト、汎用紙のペアごとのコスト、x,y,Tと列位置から計算する取っ手の局所項など。これらは変更された列の寄与を引いて足すので、現在のhcostと同じ更新範囲で済む。一方、代表donor、対象別の被覆DPと分布更新は多数の列を結び付ける。完全なVを現在のhcostと同程度の近傍コストにはできていない。

したがって、当面は**焼きなましの目的値は候補生成に使い、仕上がった候補の順位付けをVに任せる**のを推奨する。Vを直接最適化した設計への外挿は未検証。局所項だけを新目的値として使う場合も、重みと探索温度を別の実験で確認する。V×256でcurの単位にそろえられるが、今回の相関だけを根拠に目的関数全体を置き換えることは勧めない。

## 再現

既存の入力・runを読み、書き込みはこのディレクトリだけ。新しい解法の実行は不要。重い分析・ビルドはすべて共有の `runs/.lock` を取る。

```bash
# 保存状態・ラベルの抽出、訓練と検証。テストの指標は出さない。
DEVAL_MANIFEST="$PWD/solutions/deval-model/runs.tsv" \\
  bash solutions/deval-model/complete_training.sh

# FROZEN.jsonに保存済みの選択で最終学習とテスト。
flock -x /home/sato/ahc074/runs/.lock env OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=8 \\
  /home/sato/ahc074/.venv/bin/python solutions/deval-model/target_model.py \\
  --mode fast --name target_fast --final
flock -x /home/sato/ahc074/runs/.lock env OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \\
  /home/sato/ahc074/.venv/bin/python solutions/deval-model/finalize.py

# 定数表の生成、C++の特徴の照合、最終Vの生成とGCC/Clangの照合。
bash solutions/deval-model/benchmark_features.sh
bash solutions/deval-model/final_cpp.sh
flock -x /home/sato/ahc074/runs/.lock env OPENBLAS_NUM_THREADS=1 \\
  /home/sato/ahc074/.venv/bin/python solutions/deval-model/write_report.py
```

`prepare.py` は `@ops` を実測の教師に使い、`features.py` は最終設計から予測側の特徴を作る。`fit.py` はケース内回帰と検証、`metrics.py` は指定の相関・選択指標、`finalize.py` は固定したモデルのテスト評価。数値の完全な記録は `TEST_RESULTS.json`、全予測は再生成できる `models/final_predictions.npz`。キャッシュ・バイナリは `.gitignore` の対象とした。

## データのrun-id

全行の対象はseed 0–999、注文列0–7（各1024注文）。

| 変種 | 設計run | 8注文列の実測run |
|---|---|---|
'''
for line in (HERE/'runs.tsv').read_text().splitlines():
    if line=='done':continue
    v,dr,rr=line.split();text+=f'| {v} | `{dr}` | `{rr}` |\n'
(HERE/'REPORT.md').write_text(text)
print('wrote REPORT.md')
