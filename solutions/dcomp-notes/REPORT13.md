# Task13: 提出用の設計時間配分

**提出向けの推奨は `dcomp-time-target`、設計配分1.22秒。指定の記録付きGCC通常2000件とClang native500件を完了した。両設定のスコア差はどちらのコンパイラでも2SE未満であり、スコア改善を実証した変更ではない。**

改良元は`solutions/dcomp-combo-dual30`。要求処理は変更せず、別agentのpacerと統合するための設計側patchである。この版単独には要求側の時間調整を含まない。

## 現状の時間配分

`dcomp-time-profile`を作り、段の境界だけで時刻を測った。GCC既定の`20261108-231547`、Clang nativeの`20261108-231826`、各200ケース、24並列の親とのcompare。両コンパイラで親dual30と200/200 stdoutがbyte一致した。

境界計測によるコード配置等の影響と区別するため、同時実行した計測なしの親のhelper終了をsame予算の基準にする。平均はGCC1.054993秒、Clang1.038165秒、等重み平均1.046579秒。**sameを1.05秒**とした。段比率は両コンパイラの計測値の等重み平均であり、どちらのコンパイラでも同じ比率・予算を使う。

|段|GCC ms|Clang ms|共通比率|
|---|---:|---:|---:|
|窓の探索|345.630|323.826|31.9215%|
|窓の最終climb = gopt|86.186|80.882|7.9662%|
|共有anneal・区間0|122.332|117.226|11.4228%|
|共有anneal・区間1|96.977|91.525|8.9883%|
|4分岐のanneal・各区間2,3の合計|174.142|163.958|16.1216%|
|その他: setup、初期matching、全仕上げ、V、初期順序、helper|—|—|23.5796%|

窓climbとgoptはこのソースでは同一のループであり、別々に二重計上しない。候補0–3はfiller 50k＋2回match＋穴あけ＋late match、候補4/6はfiller 25k＋1回match＋穴あけ＋late match、候補5/7/8は既存の穴を引き継いで穴あけ＋late match。全候補にVが1回ある。

全候補・全段のms、比率、累積期限は[SHARES13.md](SHARES13.md)。初期matchingも固定段として計測した。比較表の`map_end_sec`だけを窓探索そのものの時間と扱わない。

## target予算の校正

自分のdual30のClang native通常500件`20261108-230504`で、req平均0.489128秒。GCC通常2000件`224255`では0.503492秒だった。時計は両方CLOCK_SCALE=1.1適用済みである。

同時比較`20261108-220933`のdual25 150件から、通常Clang nativeのreq0.494963秒、libc++＋zero-initのreq0.511245秒。対応するbuild条件の差は比で**1.03290倍**。sourceとcompilerを混同しないため、この比だけを自分のClang平均へ適用する。

```text
予想judge req = 0.489128 × 1.03290 × 1.25 ≈ 0.6315秒
custom testのその他時間 = 1.684 − 1.100 − 0.581 = 0.003秒
通常1.85秒のためのhelper終了目安 = 1.85 − 0.6315 − 0.003 ≈ 1.2155秒
```

よって**targetの設計配分予算を1.22秒**とした。最後の可変段は候補6のfillerで、累積比率93.7133%。その後の固定作業は現状平均約66msであり、余り時間を待つことはしない。1.22秒配分ならhelper終了は約1.21秒となる見込みで、最初の動作確認も平均1.210–1.211秒だった。この計算は正常時の見積りであり、judgeの速度変動への最終対応は別patchの要求pacerが担当する。

校正の全数値・flagsは`t13-shares.json`。custom test1件だけから全caseの最大時間を保証することはしない。

## 時間化した実装

`DesignTimePlan`が、設計開始時刻をoriginとして、各段に`origin + budget × 累積比率`という絶対期限を渡す。過去の遅れに対して各段の予算を再び満額加える方式にはしない。

- 窓の焼きなましとgopt、共有2区間、4分岐×2区間、6回のfiller climbを時間化。
- anneal温度は、その区間の実際の探索開始から絶対期限までの時間進捗で変化する。区間ごとのbestへの復帰、再加熱係数、乱数seed、moveの種類は元のまま。
- Hungarianの2回/1回、後段Hungarianの1回、穴あけ候補を一巡する有限パス、V、初期順序DP、helper準備は全て元の固定作業を行う。それまでの固定作業の時間は次の探索期限が吸収する。
- 期限切れならその探索は0反復でもよいが、候補自体を捨てない。9候補の仕上げ・Vを全て行い、選ばれた設計をDesignStoreへ保存する。
- 共有部分が遅くなっても、後の分岐の期限を後ろへ延ばさない。期限を超えた固定作業の費用を消す仕組みではなく、可変探索の追加消費を止める仕組みである。

`kHelperGiveUp`はこの親には存在しない。残るhelper-table cutoffは通常`1e300`で無効、保存設計を読む時だけ保存済みのreadyを再現する。その動作は維持し、helper表と列MDPを途中で欠く変更を要求ポリシーへ持ち込まない。その他の設計時計は全て`elapsed_sec()`→`scaled_since()`を使い、CLOCK_SCALEを適用した。

## 時計確認の費用

profileの設計計測後に32768回の時計読みを別に測った。平均1回GCC22.64ns、Clang23.05ns。新しい確認間隔は窓/gopt512反復、anneal/filler2048反復。

|段|GCC 推定clock費用/段|Clang 推定clock費用/段|
|---|---:|---:|
|窓探索|0.0058%|0.0063%|
|gopt|0.0068%|0.0074%|
|annealの最も高い区間|0.0362%|0.0388%|
|fillerの最も高い候補|0.0056%|0.0051%|

いずれも0.1%未満。時計費用そのものの推定であり、計測版の全体時間差を全て時計読みと帰属させてはいない。段別診断はbufferへまとめて出力する。

## 変換・期限切れ・保存設計の検証

- `DESIGN_FIXED_ITERS=1`はLOCAL_BENCHのみの回帰確認用。旧MAP_ITERS/GOPT_STEPS/ANNEAL_ITERS等を再利用し、既定では必ず時間版を使う。
- 固定反復確認`20261108-233215` GCC / `233447` Clang native、各200件。両方親dual30と**200/200 stdout byte一致**。
- `DESIGN_SECONDS=0.01`による期限切れ試験`234005`、20件。map・全anneal・fillerは全て0反復でも、全20件で9候補を完了し、正のscoreで終了した。固定作業は省略しないためhelper終了は0.37–0.47秒。任意の短い予算へ固定作業まで収める保証ではない。
- Solver本体から要求処理、mainの要求処理以降を親とbyte比較するassertをgeneratorに置いた。要求の計画・修復・予算の変更はない。
- 最終targetの保存設計を再読込した`20261109-000023`、seeds 0–49。dual30とtargetの両方が、元の通常runの出力と**50/50 byte一致**、E=0。DesignStoreが選ばれた設計を保存し、要求ポリシーが維持されている。
- GCC native、Clang native、Clang native＋libc++＋zero-initの提出用（LOCAL_BENCHなし）buildに成功。実行は行わず、binaryは`/tmp/ahc074-task13-build`だけに置いた。ローカルはGCC 13.3 / Clang 18.1.3であり、judgeのClang 21そのものをローカルで検証したわけではない。
- `design.patch`はdual30へ`patch --dry-run`で全hunk適用可能。

## 最終比較

指定の通常compareを同じ凍結ソースで完了した。負の差が改善、±はseed間の標準誤差。全runは記録済み、WA=0、E=0。ソースhash・件数・記録・表示誤りの監査は`t13-audit.json`。

### GCC既定・2000件

run: `20261108-234310_argon-des-perf-latew105`, `20261108-234310_dcomp-combo-dual30`, `20261108-234310_dcomp-time-same`, `20261108-234311_dcomp-time-target`

|候補|dual30比 % ± SE|moves/order差 ± SE|勝/分/敗|
|---|---:|---:|---:|
|dcomp-time-same|+0.044353 ± 0.025524|+0.004435 ± 0.002558|974/8/1018|
|dcomp-time-target|-0.005872 ± 0.026113|-0.000606 ± 0.002616|1010/5/985|

CLOCK_SCALE適用済みのプログラム時計。各セルは平均 / p99 / 最大、単位は秒。

|版|helper_end|req|end|
|---|---:|---:|---:|
|argon-des-perf-latew105|0.995729 / 1.136490 / 1.250320|0.444484 / 0.519710 / 0.587833|1.453831 / 1.606781 / 1.714970|
|dcomp-combo-dual30|1.049783 / 1.203119 / 1.326140|0.494388 / 0.571838 / 0.598644|1.559241 / 1.728271 / 1.827440|
|dcomp-time-same|1.049316 / 1.071725 / 1.139070|0.494541 / 0.576498 / 0.630740|1.558821 / 1.644814 / 1.764880|
|dcomp-time-target|1.208562 / 1.228801 / 1.250650|0.494992 / 0.571083 / 0.710099|1.718716 / 1.804385 / 1.969500|

dual30との対応差（ms、± SE）:

|候補|helper_end|req|end|
|---|---:|---:|---:|
|dcomp-time-same|-0.467 ± 1.501|+0.154 ± 0.974|-0.420 ± 1.828|
|dcomp-time-target|+158.779 ± 1.500|+0.604 ± 0.973|+159.475 ± 1.824|

|候補|end>1.80|>1.85|>1.90|>1.93|>2.00|
|---|---:|---:|---:|---:|---:|
|argon-des-perf-latew105|0|0|0|0|0|
|dcomp-combo-dual30|1|0|0|0|0|
|dcomp-time-same|0|0|0|0|0|
|dcomp-time-target|33|6|3|1|0|

|候補|seeds 0–999 % ± SE|seeds 1000–1999 % ± SE|
|---|---:|---:|
|dcomp-time-same|+0.039343 ± 0.036280|+0.049362 ± 0.035929|
|dcomp-time-target|-0.023467 ± 0.036517|+0.011724 ± 0.037346|

締切の診断（全caseで9候補を完了）:

|候補|0反復だった可変段（件数）|helper終了−予算終了 平均 / p99 / 最大 ms|clock読取回数 平均|
|---|---|---:|---:|
|dcomp-time-same|c1_anneal_s2:2, c2_anneal_s2:1, c2_filler:1, c4_filler:25, c6_filler:61|-1.247 / 21.003 / 88.750|6918.0|
|dcomp-time-target|c1_filler:1, c2_anneal_s2:1, c4_filler:6, c6_filler:10|-12.022 / 7.688 / 30.300|8500.8|

### Clang native・500件

run: `20261109-000022_argon-des-perf-latew105`, `20261109-000022_dcomp-combo-dual30`, `20261109-000022_dcomp-time-same`, `20261109-000022_dcomp-time-target`

|候補|dual30比 % ± SE|moves/order差 ± SE|勝/分/敗|
|---|---:|---:|---:|
|dcomp-time-same|+0.027891 ± 0.050587|+0.002785 ± 0.005073|242/0/258|
|dcomp-time-target|+0.021444 ± 0.053340|+0.002141 ± 0.005345|241/3/256|

CLOCK_SCALE適用済みのプログラム時計。各セルは平均 / p99 / 最大、単位は秒。

|版|helper_end|req|end|
|---|---:|---:|---:|
|argon-des-perf-latew105|0.933554 / 1.046785 / 1.106260|0.421579 / 0.494201 / 0.499951|1.369178 / 1.494917 / 1.530120|
|dcomp-combo-dual30|1.002172 / 1.113848 / 1.192650|0.465674 / 0.533978 / 0.603248|1.482515 / 1.613745 / 1.642160|
|dcomp-time-same|1.048293 / 1.065476 / 1.078690|0.468168 / 0.543974 / 0.584708|1.531443 / 1.626172 / 1.654850|
|dcomp-time-target|1.209054 / 1.227105 / 1.239610|0.466207 / 0.537732 / 0.557056|1.690107 / 1.771792 / 1.806410|

dual30との対応差（ms、± SE）:

|候補|helper_end|req|end|
|---|---:|---:|---:|
|dcomp-time-same|+46.121 ± 2.188|+2.494 ± 1.809|+48.928 ± 2.970|
|dcomp-time-target|+206.882 ± 2.191|+0.534 ± 1.852|+207.592 ± 3.066|

|候補|end>1.80|>1.85|>1.90|>1.93|>2.00|
|---|---:|---:|---:|---:|---:|
|argon-des-perf-latew105|0|0|0|0|0|
|dcomp-combo-dual30|0|0|0|0|0|
|dcomp-time-same|0|0|0|0|0|
|dcomp-time-target|2|0|0|0|0|

締切の診断（全caseで9候補を完了）:

|候補|0反復だった可変段（件数）|helper終了−予算終了 平均 / p99 / 最大 ms|clock読取回数 平均|
|---|---|---:|---:|
|dcomp-time-same|c4_filler:6, c6_filler:12|-1.921 / 15.304 / 28.550|7148.3|
|dcomp-time-target|c4_filler:2, c6_filler:5|-11.132 / 6.896 / 19.440|8615.9|


## 推奨と実測の読み方

**推奨は1.22秒（target）。** 正常時の1.85秒目標から、要求へ約0.60–0.63秒を残す配分である。今回のClang native最終500件ではtargetのreq平均0.466207秒。先に固定した校正比を適用すると`0.466207 × 1.03290 × 1.25 = 0.60193`秒、helper平均1.209054秒とcustom testのその他0.003秒を足して約**1.814秒**となる。事前の遅い測定（req0.489128秒）では同じ計算が約**1.844秒**。速かった今回だけを根拠に予算を増やさず、1.22秒を維持する。libc++＋zero-initによる固定尾部の数ms増も、この余裕と要求pacerで扱う。

時間化後の設計へ、旧judge modelの1.04倍を全体に機械的に掛けることはしない。探索はプログラム時計の期限で止まり、CPU速度差は主に反復数へ現れる。最後の可変段以降の固定作業については速度差・割込みが残る。要求側は未変更なので、本版単独で1.90/1.93秒終了を保証したものではない。要求pacerとの統合後の検証が、最終提出版の確認になる。

sameは事前のGCC/Clang平均から1.05秒と定めた。最終GCCの親helper平均1.049783秒にはほぼ一致する。最終Clangの親は1.002172秒と事前測定より速かったため、同じ1.05秒の配分が親比+46.1msになる。これは共通秒数を維持した結果であり、コンパイラ別の予算や、最終測定を見ての設定変更は導入していない。

同一予算での変換コストはGCCで+0.0444±0.0255%、Clangで+0.0279±0.0506%。悪化方向の点推定だが2SEには達しない。targetもGCC−0.0059±0.0261%、Clang+0.0214±0.0533%で有意差はない。したがって「増やした時間が明確な得点改善を生んだ」とは結論しない。今回確かめた効果は、たとえばGCC sameのhelper p99が親1.203119秒から1.071725秒へ、maxが1.326140秒から1.139070秒へ縮まること、targetのhelper平均が両コンパイラで1.209秒付近に安定することである。

遅延を次の絶対期限へ持ち込むので、短い探索が0反復になることはある。GCC targetのc6 fillerは10/2000件（0.5%）、Clangは5/500件（1.0%）。全ケースで固定仕上げと9候補のV比較は実行した。期限を超えた処理時間を取り戻すために、後続候補を捨てる規則はない。GCC targetのhelper終了−予定終了は平均−12.0ms、p99+7.7ms、max+30.3msで、固定尾部まで含めた厳密な上限ではない点を残す。

新たな探索中clock確認はGCCで平均6918回（same）/8501回（target）、Clangで7148/8616回。事前の1読取の平均費用を使うと一評価あたり約0.16–0.20ms、設計時間の約0.02%である。時間化により反復数と設計は実行時の速度にも依存するため、通常run間のbyte一致を期待する設定ではない。固定反復の回帰試験と保存設計の再読込で、時計制御以外の変化を検査した。

外部負荷はGCC mean0.20/max1.25core、Clang mean0.21/max1.39coreで警告なし。詳細は`t13-final-gcc.json`/`t13-final-clang.json`。現在のscore・時間だけで採用判断を調整する追加探索・追加の速いrun選別は行っていない。

## 成果物・統合

- `solutions/dcomp-time-same/main.cpp`: 1.05秒配分。
- `solutions/dcomp-time-target/main.cpp`: 1.22秒配分。
- 各ディレクトリの`design.patch`: dual30からの設計側だけの差分。要求コードの同一性は`t13-patch-audit.json`。
- dual25をcurrent、dual30をbase、targetをotherとした`git merge-file -p`は衝突なく成功し、結果の要求コードがdual25と同一であることも確認した。`dual25-time-target.preview.cpp`はport確認用であり、別solverとして評価したものではない。

3-way統合時は、pacer側のソースをcurrent、`dcomp-combo-dual30/main.cpp`をbase、`dcomp-time-target/main.cpp`をotherにする。patchは`a/main.cpp`→`b/main.cpp`というファイル名で、plain dual30に直接適用することもできる。元のファイルへ上書きせず、新しい提出版のディレクトリで統合する。

再現用の新規script: `task13_make_profile.py`、`task13_shares.py`、`task13_make_timed.py`、`task13_final_run.py`、`task13_final_stats.py`、`task13_pack.py`。全case実行は凍結済み`task10_run.py`からpahcer_run.pyへ委譲する。build・重い集計は共通flockとniceを使用。通常runは全て記録、commit・共有ファイル変更なし。

## 再評価のコマンド

同じ凍結ソースで新しいrunを作る場合（コンパイルもwrapper内のflock/niceを経由する）:

```sh
nice -n 10 python3 solutions/dcomp-notes/task10_run.py --compare solutions/argon-des-perf-latew105 solutions/dcomp-combo-dual30 solutions/dcomp-time-same solutions/dcomp-time-target --seeds 0-2000 --save-design -c "Task13 GCC verification"
DEVAL_CXX=clang++ DEVAL_NATIVE=1 nice -n 10 python3 solutions/dcomp-notes/task10_run.py --compare solutions/argon-des-perf-latew105 solutions/dcomp-combo-dual30 solutions/dcomp-time-same solutions/dcomp-time-target --seeds 0-500 --save-design -c "Task13 Clang native verification"
```

`task13_final_run.py`は今回の凍結記録を上書きしないため既存の`t13-freeze.json`があれば停止する。今回のrunを再集計する場合は`task13_final_stats.py`へ4つのrun-id、`--count`、`--output`を渡し、common lock/nice下で実行する。`RESULTS13.md`は最終集計JSONからの表生成物。
