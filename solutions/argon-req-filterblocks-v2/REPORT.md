改良元: solutions/argon-des-design-packed

R2の追加候補を増やす前に、要求処理の時間を出力不変で確保する検討。最終候補は `main.cpp`。ejectstats や探索予算の変更は含めない。

PR141のstratacutで開発し、全件確認中にBASE.mdがPR142のdesign-packedへ更新されたため移植した。変更前の対象節が両基準でバイト一致することを確認し、その節だけを置き換えた（port.txt）。最終採否はPR142に対する通常2000件と固定設計2000×2で判断する。以下の開発時の数値とプロファイルは、特記した最終比較以外はPR141基準である。

## 変更と厳密性

`Post-processing: deletions and new anchors of the edits` 内の `PostContext`、`prepare_post_context`、`post_optimize::evaluate` だけを変更した。目次・節名は不変。PR141では9112 → 9115行、PR142では9143 → 9146行。Solverの総サイズと他メンバのオフセットを変えない。

1. **区間境界の一括構築。** 移動する紙の集合 M とアンカーの集合 A を、紙番号ではなく初期積層の位置のビット集合で表す。元の境界集合は厳密に `A | M | (M >> 1)` であり、192ビットの右シフトを3語で計算する。語の間の桁移動は次の語の最下位ビットを前の語の最上位へ渡す。先頭の紙の直前は集合外へ捨てる。候補の編集順、リンクの付け替え順、境界集合は不変。
2. **1枚の区間を直接参照。** 初期位置 i が境界なら `next_break(i) == i`。移動紙でなくてもこの区間は1枚であり、旧sparse tableの長さ1の問い合わせはその紙の被覆・色と等しい。境界の確認後は直接参照する。
3. **同時に読む2語を隣接配置。** 被覆・表示色の2配列を `Block { u64 cov, disp; }` の配列にまとめる。配列の全バイト数は同じで、区間の合成式 `cov_left | cov_right` と `disp_left | (disp_right & ~cov_left)` も同じ。長さ1の区間もこの表から読む。

以上は整数演算と記憶配置だけの変更。候補を省かず、目的関数・浮動小数点演算順・合法性再生・キャッシュのキーやアクセス回数・探索予算を維持する。設計・DesignStore・緊急設計は変更していない。後続の研究用ログ、全指標、プロファイラ、実験スイッチは残した。

## 最初のプロファイル

固定設計 `20261106-032942_argon-des-perf-stratacut`、48 seed × 2注文列。`20261106-041055_argon-req-exactprofile` は新基準にF3_PROFILEとCOLFAST_PROFILEだけを有効にした版。

1ケース平均の排他時間は、最終表示チェック91.169 ms、次状態価値64.869 ms、eject候補生成63.661 ms、合法性再生50.603 ms、prelift filler構成26.148 ms、joint DP24.229 ms、neutral候補生成23.682 ms、正規化21.619 ms。evaluateは746,183回、合法性再生は216,233回、次状態価値は108,221回。要求全体は時計を含め577.855 ms。

F3_PROFILEでは、初期計画のre-anchorが57.558 ms、ejectが75.223 ms、中立候補の再編集のre-anchorが合計64.912 ms。これらに共通する表示フィルタを最初の対象にした。計測時計の費用が大きいため、採否は時計を追加しない通常版の同時比較で判断する。

## 試した実装

すべて評価は `scripts/pahcer_run.py`。通常評価は記録し、固定設計評価は仕様どおり非記録。下表の時間は各行で同じ比較の両腕から求めた。小範囲の差を独立した確定値として足し合わせてはいない。

| 候補 / run接頭辞 | 範囲 | 基準→候補 req_sec | 比 | 判断 |
|---|---|---:|---:|---|
| wrongmask / 20261106-041841 | 固定48×2 | 0.457215→0.450114 | 0.984470 | 通常で再確認 |
| planstorage / 同上 | 固定48×2 | 0.457215→0.455504 | 0.996258 | 小差、含めない |
| earlyscan / 同上 | 固定48×2 | 0.457215→0.460765 | 1.007765 | 含めない |
| wrongmask / 20261106-042113 | 通常200 | 0.446785→0.446876 | 1.000204 | judge平均+11.55 ms、含めない |
| valuekey / 20261106-042948 | 固定48×2 | 0.459241→0.459415 | 1.000379 | 含めない |
| filterbits / 同上 | 固定48×2 | 0.459241→0.447275 | 0.973945 | 通常へ |
| keybits / 同上 | 固定48×2 | 0.459241→0.446241 | 0.971693 | キー変更の追加効果は小さく含めない |
| filterbits / 20261106-043302 | 通常200 | 0.442421→0.434580 | 0.982276 | judge平均+1.23 ms、全体の条件未達 |
| filtermask / 20261106-043901 | 通常200 | 0.445210→0.433512 | 0.973726 | judge平均−14.28 ms |
| filterblocks / 20261106-044052 | 通常200 | 0.444376→0.431473 | 0.970963 | judge平均−18.40 ms、最終確認へ |
| findhead / 20261106-044334 | 固定48×2 | 0.457765→0.458333 | 1.001240 | 含めない |

wrongmaskは区間表の黒色を要求との誤色に変える案。filtermaskはそれと境界一括構築の結合。filterblocksとの小差だけで優劣は断定せず、表示表の意味と演算を保つfilterblocksを最終候補にした。planstorageは一時配列の動的確保削減、earlyscanは走査の早期終了、valuekeyは次状態価値のキーの分岐なし構築、findheadは紙位置検索の先頭16枚をSSE2で調べる案。

全候補の上記範囲でstdoutと全非時刻stderrは一致、WA / self_wrong / op_label_errorsは0。`20261106-042948` の終了処理にはworkerのInterrupted表示があるが、全48×2・全4腕の結果とファイルを確認済みで、評価プロセスも正常終了している。最終採否は別の大規模比較で行う。

filterbits単独の両腕プロファイル `20261106-043303_argon-req-exactprofile` / `20261106-043303_argon-req-filterbits-profile` は、表示チェック91.514→80.957 ms、要求全体579.546→569.481 ms。プロファイラの非時刻欄も96/96一致した。一方、通常200件では無変更のmap段が約14.7 ms増えて全体では相殺された。Solverサイズの不変だけで全体時間の改善を保証できないため、全体の同時比較を必須とした。無変更段の時差の原因を特定したとは主張しない。

## 最終確認

**採用条件を満たす。マージ対象は `solutions/argon-req-filterblocks-v2/`。** ソースはPR142の基準と、上記の後処理節以外がバイト一致する。変更後の節はPR141版filterblocksとバイト一致し、移植時に手法を変えていない。行数は9143 → 9146。最終ソースのSHA-256は `7d123e16ca21cf6cfb9f4e538760f9e5e583440c8f67559900ec0333bbe622f1`。

通常2000 seed（`--save-design`）:

- 基準: `20261106-045419_argon-des-design-packed`
- 候補: `20261106-045419_argon-req-filterblocks-v2`
- logスコア比 **0.000000 ± 0.000000%**、勝/分/敗 **0/2000/0**、WA=0。
- stdoutと全非時刻stderrが **2000/2000でバイト一致**。@paper、@ops、全既存メトリクス、キャッシュの回数も一致。全件self_wrong=0、op_label_errors=0。
- 両腕で2000件の設計を保存した。次回は `--design-from 20261106-045419_argon-req-filterblocks-v2` を使える。

| 指標 | 基準 | 候補 |
|---|---:|---:|
| map_end_sec 平均 | 0.449832 | 0.451384 |
| helper_end_sec 平均 | 0.923133 | 0.923340 |
| req_sec 平均 | 0.442468 | 0.430710 |
| end_sec 平均 | 1.379390 | 1.367801 |
| judge-model 平均 | 1.571179 | 1.555483 |
| judge-model p99 | 1.744137 | 1.714582 |
| judge-model 最大 | 1.854298 | 1.871765 |
| judge-model 2秒超え件数 | 0 | 0 |

req_sec比は **0.973427**（**2.657%短縮**）。要求時間の差は **-11.758 ± 0.701 ms**、judge-model平均の差は **-15.696 ± 1.591 ms**（対応するseed差の平均±SE）。5 ms以上短縮する条件を満たす。p99も低下し、最大値は少し増えたが両腕とも2秒未満。無変更のmapとhelperまでの累積時間も表に載せ、要求段だけの改善で全体が遅くなっていないことを確認した。外部負荷は平均0.13・最大0.39コア。

固定設計2000 seed × 2注文列:

- 保存設計: `20261106-043249_argon-des-design-packed`
- 基準: `20261106-045420_argon-des-design-packed`
- 候補: `20261106-045420_argon-req-filterblocks-v2`
- stdoutと全非時刻stderrは **4000/4000でバイト一致**。logスコア比0、SE 0、勝/分/敗0/2000/0、WA / self_wrong / op_label_errorsすべて0。
- req_secは **0.456118 → 0.443346 s**、比 **0.971999**（2.800%短縮）。外部負荷は平均0.19・最大0.59コア。固定設計の絶対end_secは保存元の設計時刻を含むので、judge時間の採否には上の通常比較を使った。

GCCとClangの `-std=c++23 -O2 -Wall -Wextra`、LOCAL_BENCHあり・なしの4構成が警告0。通常・固定の保存ソースは最終main.cppと一致した。検証と時間の生値はfinal-analysis.log、normal-results.json、fixed-results.json、paired-times.json、builds.logにある。BASE.mdは最終比較前と報告前に読み直し、PR142が基準のままであることを確認した。

## プロファイルとスイッチの保持

PR141上での最終手法の同時プロファイル、48×2:

- `20261106-044522_argon-req-exactprofile`
- `20261106-044522_argon-req-filterblocks-profile`

| 処理 | 基準 ms | 候補 ms |
|---|---:|---:|
| 表示フィルタ・排他 | 90.949 | 78.970 |
| 区間表準備・排他 | 1.243 | 1.057 |
| 合法性再生・排他 | 50.471 | 50.657 |
| 次状態価値・排他 | 64.091 | 65.534 |
| 後処理全体・包含 | 426.837 | 417.633 |
| 要求全体・包含 | 575.920 | 574.762 |

表示フィルタは約13.2%短縮。全候補数746,183回、合法性再生216,233回、値計算108,221回、全F3段別の試行・採用・利得と非時刻のprofiler欄が一致した。一方、時計入り版では無変更のjoint DP等の時間が増え、全体の短縮は小さい。プロファイルの総時間を通常版へ外挿せず、採否は通常版2000件の値で判定した。全表は `../argon-req-filterblocks-profile/profile-summary.json`。

実験スイッチは、基準へ意図しない設定を渡すcompareを避け、同じ設定の単独評価をそれぞれpahcerで実施して照合した。これもPR141上で行い、移植後の要求処理の変更部分は同一である。

| 設定 | 範囲 | 基準run | 候補run | 結果 |
|---|---|---|---|---|
| F3_MODE=2、NS_TRIPLES=1、NS_INTERIOR=4、HEAVY_TRACE=1、HEAVY_PREDICT=1（全てF3_） | 4×1 | 20261106-044718_argon-des-perf-stratacut | 20261106-045335_argon-req-filterblocks | 全stdout・非時刻stderr一致、heavy/heavycand出力も一致 |
| F3_MEMO=0、F3_PREFIX=0、COLMDP=0 | 8×2 | 20261106-045356_argon-des-perf-stratacut | 20261106-045418_argon-req-filterblocks | 全stdout・非時刻stderr一致、MDP無効とmemo hit 0を確認 |

全スイッチ検証でWA / self_wrong / op_label_errorsは0。section marker、目次、全ログ・指標・profiler・既存スイッチ・DesignStore・CLOCK_SCALEを保持し、新規指標は増やしていない。

## PR141での先行全件確認

通常2000件 `20261106-044052_argon-des-perf-stratacut` / `20261106-044052_argon-req-filterblocks`: stdout・全非時刻stderrは2000/2000一致。req_sec 0.443738 → 0.431141 s、比0.971612。judge平均1.602098 → 1.584937 s、p99 1.788731 → 1.782255 s。最大1.953932 → 2.017080 s、2秒超え0 → 1件だった。外部負荷は追加1800件で平均0.25・最大1.39コア。この旧比較の絶対時間を新基準に流用せず、上記のPR142同時比較をやり直した。

固定2000×2 `20261106-044521_argon-des-perf-stratacut` / `20261106-044521_argon-req-filterblocks`: 4000/4000一致、req_sec 0.457652 → 0.444059 s、比0.970299。いずれも全件同点・WA 0。先行版の4構成ビルドも警告0。

再現例:

```sh
python3 scripts/pahcer_run.py --compare solutions/argon-des-design-packed solutions/argon-req-filterblocks-v2 --seeds 0-2000 --save-design -c 'exact request filter final'
python3 scripts/pahcer_run.py --compare solutions/argon-des-design-packed solutions/argon-req-filterblocks-v2 --design-from 20261106-043249_argon-des-design-packed --seeds 0-2000 --orders 2 -c 'exact request filter fixed'
```

解析は保存済み出力だけを読み、whenidle.sh経由・共有lock・1コアで実行した。ソルバーやテスターの直接実行、コミット、共通スクリプトやtrial_log.mdの編集は行っていない。

## 残る作業

時間短縮の採用条件を満たしたため、指示どおりここでマージ待ちにする。ejectstatsは未採用で、新しいBASE.mdと設計で再測定が必要。completeold-full、第二DP解候補の押し出し、seededit-wide、その後のR3〜R5は未完了で、この検討を理由に閉じない。
