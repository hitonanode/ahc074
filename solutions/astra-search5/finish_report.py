#!/usr/bin/env python3
"""確定した採用版の数値を生データからまとめる。提出ソースは変更しない。"""
from pathlib import Path
import csv, datetime, hashlib, json, math, statistics
h=Path(__file__).resolve().parent
labels=['selected-main-normal','holdout-main-normal']
summaries={label:json.loads((h/(label+'.json')).read_text()) for label in labels}
adoption=json.loads((h/'adoption.json').read_text())
source=(h/'main.cpp').read_bytes()
assert hashlib.sha256(source).hexdigest()==adoption['retained']['main.cpp']['sha256']
table=[]; final_rows=[]
for label,title in zip(labels,['選定64件（24〜87）','採用後64件（300〜363）']):
    d=summaries[label];c=d['compare']['gobj_after'];v=d['variants']
    table.append(f"| {title} | {v['base']['gobj_after']['mean']:.6f} | {v['main-bin']['gobj_after']['mean']:.6f} | {c['log_pct']:+.4f} ± {c['se_pct']:.4f}% | {c['win']}/{c['tie']}/{c['loss']} | {v['main-bin']['end_sec']['max']:.5f} |")
    final_rows += [dict(r,label=label) for r in csv.DictReader((h/(label+'.csv')).open()) if r['binary']=='main-bin']
worst=max(final_rows,key=lambda r:float(r['end_sec']))
assert float(worst['end_sec'])<=1.75
assert all(float(r['Score'])>0 and float(r['self_wrong'])==0 and float(r['fast_requests'])==0 and float(r['G'])==36 for r in final_rows)
verify=json.loads((h/'verify-main-fixed.json').read_text())
checks={k:round(v['mean']*8) for k,v in verify['variants']['verify-main-bin'].items() if k.startswith('verify_')}
clang=json.loads((h/'clang-main-fixed.json').read_text())
assert verify['compare']['gobj_after']['tie']==8 and clang['compare']['gobj_after']['tie']==8
build=json.loads((h/'build-info.json').read_text())
base=(h.parent/'astra-search4/main.cpp').read_text();s=source.decode()
def parts(text):
    p=text.index('WindowStats assign_windows(');q=text.index('// kBitLanes',p)
    m=text.index('    auto matching_cost =',p);n=text.index('    // A move:',m)
    return text[:p],text[q:],text[m:n]
assert parts(base)==parts(s)
(h/'scope-summary.json').write_text(json.dumps({'main.cpp':{'outside_assign_windows_unchanged':True,'matching_cost_unchanged':True,'sha256':hashlib.sha256(source).hexdigest(),'base_sha256':hashlib.sha256(base.encode()).hexdigest()}},indent=2)+'\n')
validation={'fixed_check_counts':checks,'gcc':build['main-bin']['compiler'],'clang':build['main-bin-clang']['compiler'],'gcc_clang_gobj_ties':8,'rebuild_gobj_ties':8,'normal_cases':len(final_rows),'normal_WA':0,'normal_self_wrong':0,'normal_fast_requests':0,'normal_G':36,'normal_end_max':float(worst['end_sec']),'normal_end_max_seed':int(worst['seed']),'helper_papers_min':min(float(r['helper_papers']) for r in final_rows)}
(h/'validation-summary.json').write_text(json.dumps(validation,indent=2)+'\n')
(h/'final-summary.json').write_text(json.dumps(summaries,indent=2)+'\n')
now=datetime.datetime.now(datetime.timezone.utc);start=datetime.datetime(2026,11,2,3,15,51,tzinfo=datetime.timezone.utc)
elapsed=(now-start).total_seconds()/60
main=summaries[labels[0]]['variants'];hold=summaries[labels[1]]['variants']
text=f'''# 窓の割り当て探索の5回目の改良

## 1. 要約

**採用候補は [main.cpp](main.cpp) の1つ。** 基準は `solutions/astra-search4`。
交換可能な窓と色をまとめて列挙し、同じ状態では重複なく選ぶ。停滞から脱出するまでの試行数を256/512にする。
目的値 `gobj_after` の改善を、採用後の別64件でも確認した。差はケースごとの100 log(候補/基準)の平均 ± 標準誤差で、負が改善。

| ケース | 基準平均 | 採用版平均 | gobj_after log比 ± SE | 勝/分/敗 | 採用版end_sec最大 |
|---|---:|---:|---:|---:|---:|
{chr(10).join(table)}

通常実行128件の `end_sec` 最大は **{float(worst['end_sec']):.5f}秒**（seed{worst['seed']}、CLOCK_SCALE込み）で、全件1.75秒以下。
WA・自己検査での誤表示・軽量モード使用はいずれもゼロ、汎用窓は全件36、補助紙登録数の最小は{validation['helper_papers_min']:.0f}。
本番2000件の最終スコア評価とsim_movesの測定は行っていない。

低温版と近傍比率変更版は探索時には2SEを超えたが、整理後の再確認はそれぞれ **−0.1617 ± 0.1094%**、**−0.1992 ± 0.1099%**にとどまった。
再確認でも2SEを超えた主案だけを残し、cand2/cand3は残さない。
採用決定は {adoption['decided_at']}（UTC）。この時点から提出ソースを変えず、seed300〜363を測定した（[adoption.json](adoption.json)）。
探索用64件を多数の候補に繰り返し使ったため、独立した検証はseed300〜363である。

作業開始は2026-11-02 12:15:51 JST、報告書確定は{now.astimezone(datetime.timezone(datetime.timedelta(hours=9))).strftime('%Y-%m-%d %H:%M:%S JST')}、経過約{elapsed:.1f}分。指定の2時間以内。

## 2. 改良の内容

### 不適合な交換の引き直しを避ける

基準は汎用窓a、ハンドル窓b、色を無作為に選び、70対のうち3対以上を不適合にする交換を除外する。
現在の状態で既に除外された交換にも乱数生成・キャッシュ照会を繰り返す。

新版では、交換元aをその状態で初めて選んだとき、ハンドル28窓×2色の**56候補をまとめて調べる**。
基準の `swap_losses` が持つ「aを外したDAGで追加できない方向」のビット集合を使い、各候補が不適合にする対数をpopcountで数える。
3対未満の候補だけを、色ごとの2本の64bit集合に保存する。候補を選んだらそのbitを消し、同じ状態では繰り返し提案しない。
状態を受理したら世代番号を進め、全ての候補表を無効にする。

交換元の窓の選び方は無作為のまま。列挙した交換先も無作為に選び、全商品対の関係更新と元のmatching_costで評価する。
近似による除外境界は3対のまま。目的関数やその貪欲マッチングを変更したものではない。

### 候補生成に合わせて停滞判定を調整する

1試行で全対評価まで進む率が増えるため、観測済みの最良近傍に進むまでの試行数を
焼きなまし **1024→256**、最後の区間 **2048→512**へ変更する。
短くしすぎた32/64、64/128試行は、近傍を調べる前に移動するため悪化した。
両区間とも訪問した最良状態を保存し、最後にその状態を返す。

窓交換率0.6、残りの近傍比率（色反転:汎用窓同士の組交換:組移動）3:5:2、温度0.05→0.00125、逆手禁止4受理分は基準と同じ。
採用版の全対評価数は、選定64件で平均 {main['base']['search_exact_evals']['mean']:.0f}→{main['main-bin']['search_exact_evals']['mean']:.0f}回、
別64件で {hold['base']['search_exact_evals']['mean']:.0f}→{hold['main-bin']['search_exact_evals']['mean']:.0f}回だった。
試行数そのものは候補をまとめて調べるため減る。回数の増加だけをスコア改善の根拠には使わない。

変更はassign_windows内だけ。関数の前後とmatching_costは基準とバイト一致する。
係数1800 / 5 / 144、距離上限26、kMapEnd=0.50 / kGoptEnd=0.61、他の段、固定乱数seed、CLOCK_SCALEを維持した（[scope-summary.json](scope-summary.json)）。
追加指標 `window_rows` は列挙した窓数の累計、`window_samples` はそこから提案した交換数。

## 3. 計測の手順と生データ

### 通常ビルドの比較

コンパイルは `g++ -std=c++23 -O2 -DCLOCK_SCALE=1.1`。
`/home/sato/ahc074/tools/target/release/tester` 経由で、8seedずつ**基準8個＋候補8個の解法を同時実行**する。
seedごとに起動順を交互にし、次のバッチで順番を反転する。CPU固定はしない。
16という上限は指定どおり解法プロセスの数で、これに公式テスター16個と集計Pythonが加わる。
各比較は前の比較が終わってから起動し、採用版の計測中はコンパイルを重ねていない。
MAP_ITERS / GOPT_STEPS / ANNEAL_ITERS / CLIMB_ITERS / SIM_SEQSを環境から除き、通常の時間制で測定する。
比較量は `d_s = 100 log(候補_s / 基準_s)`、標準誤差はd_sの標本標準偏差/√64。
異なる計測ラベルの小さな差から、候補同士の優劣を確定しない。

主な生データ:

- [selected-main-normal.csv](selected-main-normal.csv): 整理後の採用ソース、seed24〜87。採用の根拠。
- [holdout-main-normal.csv](holdout-main-normal.csv): 採用決定後のseed300〜363。
- [final-summary.json](final-summary.json): 上記2比較の全指標の集計。
- [EXPERIMENTS.md](EXPERIMENTS.md): 全比較のlog比・SE・勝分敗・end_sec。各ラベルのCSV/JSONが対応する。
- [experiments-config.json](experiments-config.json): 実験ソースの再生成パラメータ。`variants.py`で再生成できる。
- [build-info.json](build-info.json): コンパイラ、指定オプション、ソースのハッシュ。
- [validation-summary.json](validation-summary.json): 正しさと制限時間の検査結果。

再実行（同名の計測ラベルは上書きしない）:

```sh
python3 solutions/astra-search5/build.py base main
python3 solutions/astra-search5/measure.py reproduce-select base main-bin
python3 solutions/astra-search5/measure.py reproduce-holdout base main-bin --seeds 300-364
python3 solutions/astra-search5/build.py main --compiler clang++
python3 solutions/astra-search5/verify.py main
python3 solutions/astra-search5/build.py verify-check
python3 solutions/astra-search5/measure.py reproduce-verify main-bin verify-check-bin --fixed 200000 --seeds 24-32 --pairs 3
```

### 正しさの診断

固定回数の診断は性能の採否に使わない。seed24〜31、割り当て200000試行＋最後50000試行、後段1024試行・最後の山登りなし、3組同時。
採用版の診断コピーで、窓交換の損失数 **{checks['verify_swaps']}件**、列挙した交換候補の可否 **{checks['verify_windows']}通り**、
組移動の可否・費用差 **{checks['verify_transfers']}方向**、返却状態の **{checks['verify_states']}商品対**を全制約の再計算と照合し、不一致ゼロ。
返却状態の目的値は元のmatching_costで再計算した。

GCC 13.3.0 / Clang 18.1.3でビルドできた。通常実装・診断実装・Clang実装は、この固定条件8件のgobj_after・全対評価回数・最終手数が全一致した
（[verify-main-fixed.csv](verify-main-fixed.csv)、[clang-main-fixed.csv](clang-main-fixed.csv)）。
列挙カウンタのビット並列化とpopcnt属性についても、変更前後の固定条件8件の一致を確認した（bit-fixed.csv / native-fixed.csv）。

## 4. 試してだめだった案

全体の数値は [EXPERIMENTS.md](EXPERIMENTS.md)。以下は主な知見で、各差はseed24〜87の64件、基準は毎回同時実行したastra-search4。
改善方向でも2SEに届かないもの、または採用版への上積みを示せなかったものもここに含む。

- **早すぎる停滞脱出:** row32（32/64試行）+1.1072 ± 0.1027%、row64（64/128試行）+0.3657 ± 0.1230%。不採用。
- **遅い停滞脱出:** row512（512/1024試行）−0.1533 ± 0.1114%。最後の区間だけ128にするrow-c128も−0.0485 ± 0.1112%で未確定。
- **現マッチングの概算費用で交換を優先:** rankは−0.2824 ± 0.1021%、rank256は−0.2246 ± 0.1030%。候補生成費用が増え、単純列挙への上積みは確認できなかった。
  不適合対の概算追加費用は3600。窓を外し、新しい窓を加えたときの70対の費用差を計算するが、採否には元の目的関数を使う。
- **複数の交換元から概算最良を選ぶ:** rank-tour2は+0.0016 ± 0.1137%、rank-tour4は+0.3642 ± 0.0971%。強い事前順位付けは改善しなかった。
- **概算費用で追加除外:** rank-cut7 / rank-cut14（費用増加上限7200 / 14400）は−0.2941 ± 0.1038%、−0.3069 ± 0.1018%。単純列挙を上回る根拠がなく不採用。
- **列挙時のビット並列カウンタ:** bit128は−0.0503 ± 0.1069%。結果を保つ実装だが、固定回数の診断でも従来のpopcount列挙より速くならなかった。
  ハンドル差分と損失数だけによる簡易順位付け（cheap128）は−0.1963 ± 0.1110%。
- **近傍比率:** kind50 / rate40 / rate80で組移動を増やす。rate80は探索時−0.3433 ± 0.0910%だったが、整理後のselected-cand3は−0.1992 ± 0.1099%。追加候補として残さない。
- **温度:** row-temp25（1/4）は探索時−0.3717 ± 0.1038%、整理後のselected-cand2は−0.1617 ± 0.1094%。1/2のrow-temp50、悪化の確率受理を止めたrow-temp0も試したが、主案の再現性を優先した。
- **状態の再訪禁止:** 現在の窓・組・色のハッシュを記録し、16 / 64受理以内の再訪を禁止するrow-state16 / row-state64は−0.1009 ± 0.1072%、−0.1595 ± 0.1068%。未確定。
- **近傍生成へのpopcnt属性:** row-nativeは−0.3349 ± 0.1059%。固定回数の結果は同じで、速度の上積みは確認できなかった。
- **窓交換と組変更の複合手:** 窓aを外し、別の組へハンドル窓bを入れる。窓交換の1/4・1/16・1/64に混ぜたrow-cross4/16/64は−0.2426 ± 0.1053%、−0.1351 ± 0.0945%、−0.1606 ± 0.0934%。
  1/4版でも提案平均71783回、全対評価932回、受理29.3回で、多くが除外された。採用版への上積みは確認できなかった。

探索初期のrow-normalは最初のバッチにコンパイル終盤が重なった可能性があるため参考値とし、採用の根拠には使っていない。

## 5. 残りの案

1. **候補表の差分更新。** 受理時に70対の大部分が残ることを利用し、候補表を全て無効にせず、変わった対・閉包の分だけ直す。今回の改善は重複した提案の除去まで。
2. **複合手を作る前に絞る。** 無作為な窓交換＋組変更は約99%が全対評価前に除外された。外した窓のDAGから許される組と色をまとめて計算できれば、違う探索経路を安く増やせる可能性がある。
3. **最終スコアへの効果。** 今回は指定どおりgobj_afterで選んだ。既知の約0.4倍という関係は目安であり、本番2000件のケースごとのスコア比で確認する必要がある。

既存ファイルは編集せず、作成・編集はsolutions/astra-search5以下だけ。pahcer_run.py、gitのcommit・push・stash・checkoutは実行していない。
実行ファイル、不採用の中間C++、個別エラーログは削除し、採用ソース、日本語説明・報告、数値記録と再実行用スクリプトを残した。
'''
(h/'REPORT.md').write_text(text)
print(json.dumps({'end_max':validation['normal_end_max'],'end_max_seed':validation['normal_end_max_seed'],'elapsed_minutes':elapsed,'checks':checks},ensure_ascii=False))
