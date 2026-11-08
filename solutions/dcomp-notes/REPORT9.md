# Task 9: 窓探索の高速化で10候補目を払う

最終候補は **solutions/dcomp-ten-fast**。通常2000件でlegal-tie-fix比 **-0.01471 ± 0.00328%**、nine比 **-0.00025 ± 0.00174%**。10候補目を加えてもhelper_endはnine比 **-20.70 ± 1.08 ms**、judge平均はargon比 **1.07402倍**。10候補目を追加してもnineの設計時間以下に収まり、平均時間のargon比1.10以下も満たした。Task9の時間資金を作る目標を達成した。

## 変更と不変条件

WindowPairsの状態用・作業用のrelation費用配列に、それぞれ非ゼロ要素の一覧を付けた。試行の初めに作業用配列の前回の非ゼロだけを消去する。旧互換ペアでraw relationが変わらないものの費用と、今回閉包を計算して非循環だったものの費用だけを書き、その他はゼロのままにする。受理時は、費用配列とその非ゼロ一覧を対にして交換する。annealからclimbへの移行では、再構築した状態の一覧を更新する。

互換ペアは「旧互換かつrelation不変」と「今回新たに非循環」の和集合である。この集合を小さなbitsetに入れて昇順に列挙する。元の全走査と同じ順序なので、matchingの同点処理、受理、乱数列まで保つ。単純なリスト併合は分岐が増えて遅かった。bitsetによる列挙と、疎な費用更新の組合せで短縮した。

追加メモリは2本の互換ペア一覧と一時bitset。一覧は通常約160要素ずつ、bitsetは最大512個のu64のstack領域のうちP.words分だけ初期化・利用する。新しい近似演算、fast-math、探索の省略はない。

10候補目(id=9)は、その時点の最良の完成割当と穴から後段rematchとVだけを実行する。climb、前rematch、穿孔探索は追加しない。既存9候補のsalt、予算、評価式、順序と選択規則は元のまま。初期列順DPを最後の選択設計に適用し、その設計をDesignStoreへ保存する。

map450k、gopt133k、annealと既存仕上げは固定反復数。時間不足の軽量化、設計cap、時刻による候補数変更は加えていない。注文処理はdcomp-nineと同じlegal-tie-fast。M1、combo-m1-nineや未コミットのlegal-*は読んでいない。

## 高速化の比較

Task 8のprofileを起点に、window約479ms、anneal約396ms、finishing約214msを対象とした。すべて通常runnerの24並列による同時比較。±はseed間の対応差の1標準誤差。表の時間はdcomp-nineからのhelper_end差で、負が速い。すべてGCC既定・500件でstdoutがbyte単位で一致した。

| 案 | helper_end差 (ms) | 判定 | run群 |
|---|---:|---|---|
| column_moveの差分構築と評価を融合 | +7.65 ± 1.87 | 不採用 | 120548 |
| 同案、新countsの保存を受理まで遅延 | −1.50 ± 1.84 | 明瞭な短縮なし | 120548 |
| 互換一覧を2本の昇順リストで併合 | +52.41 ± 2.52 | 不採用 | 120857 |
| 同案＋非ゼロ費用だけ更新 | +18.75 ± 2.74 | 不採用 | 121546 |
| relationのbit packingを直接PEXTへ | −0.77 ± 1.64 | 明瞭な短縮なし | 121724 |
| single同士の交換で不変な二次費用を省略 | +5.77 ± 1.97 | 不採用 | 121935 |
| SIMD方向flagを表引きから直接展開へ | +12.15 ± 1.83 | 不採用 | 122325 |
| 互換集合をbitsetから昇順列挙 | −7.87 ± 2.07 | 単体の短縮は小さい | 122540 |
| **bitset列挙＋非ゼロ費用だけ更新** | **−37.76 ± 2.11** | 採用候補 | 122540 |
| 全走査を32 laneのpackと列挙へ | +7.16 ± 2.46 | 不採用 | 122749 |
| **採用案の再比較 (nine-fast)** | **−25.46 ± 2.57** | 短縮を再現 | 123149 |
| **採用案＋10候補 (ten-fast)** | **−22.50 ± 2.49** | 10候補でもnine以下 | 123149 |

日付接頭辞はすべて`20261108-`。完全なrun-idは`t9-experiments.json`に保存した。採用案のmap_end差は初回−39.30±1.81ms、再比較−28.70±1.89ms。2回の短縮幅には差があるため、最大値だけを成果として扱わず、最終比較の対応差も示す。採用案の初回・再比較の外部負荷はそれぞれ平均0.13/0.17 core、最大0.27/0.62 core。

10候補目の選定根拠はTask8の訓練500件・新規lists1–7、nine比−0.00448±0.00140%（tenのreplay `20261108-113054_legal-tie-fast`対nineの`20261108-112306_legal-tie-fast`）。今回はこの10候補政策を変更せず、高速化だけを組み合わせた。通常比較や未見replayでの増分は下で別に示す。

## コンパイラ・候補の同一性

| 条件 | 件数 | 親nineとのstdout一致 | nine-fastのhelper_end差 (ms) | run群 |
|---|---:|---:|---:|---|
| GCC C++23 -O2（既定） | 500 | 500/500 | −25.46 ± 2.57 | 123149 |
| GCC C++23 -O2 -march=native | 200 | 200/200 | −22.24 ± 4.25 | 123212 |
| Clang C++23 -O2 -march=native | 200 | 200/200 | +80.30 ± 4.73 | 123214 |

比較はそれぞれのコンパイラでビルドした親との一致である。**性能改善はGCC側で確認した。Clangは正しさ・同一性を満たすが遅くなった。** 提出先のGCCを前提に評価し、Clangでも高速化したとは主張しない。LOCAL_BENCHを付けない提出形式でもGCC・ClangのC++23 nativeビルドが成功した。

10候補への変換を元のnineへ適用すると、凍結したten-lateのソースと文字列単位で完全一致する。nine-fastの窓以降はnineと、ten-fastの窓以降はten-lateと完全一致（`t9-source-audit.json`）。ten-fastのstdoutも、旧ten-lateの`20261108-112915`と500/500 byte一致した。

診断run `20261108-123401_{dcomp-nine-audit,dcomp-ten-audit}`、200件では、最初の9候補のDesignState全設計値、raw unit割当、RNG、curとVのdouble bit表現が **1,800/1,800候補で完全一致**。選択は全件で最初のargmin Vと一致。10候補目を選ばなかった175件は最終stdoutも一致し、選んだ25件はVが厳密に改善した（`t9-candidate-check.json`）。診断用の追加出力は最終ソースには入れていない。

## 凍結と最終2000件

凍結時刻は2026-11-08 12:39:24 JST。main.cppのSHA256は`b30828b092bd40a0bd1164380046d6cf0b695a789874e37106a42b9c5ac10303`、533,860 bytes。本Taskの指示どおりサイズ削減は行っていない。設定選択はseeds0–499までで、凍結後に設定・ソースを変更しない。

差は`100 × mean(log(candidate/reference))`。±は1標準誤差。judgeモデルは`1.04×helper_end_sec + 1.35×req_sec + rest`。最終run群は`20261108-123924`、指定のargon、legal-tie-fix、dcomp-nine、dcomp-ten-fastの順で、`--no-record`なし、`--save-design`あり。

<!-- FINAL_START -->
| 候補 | 基準 | seeds | 差 (%) | 勝/分/敗 |
|---|---|---|---:|---:|
| dcomp-nine | legal-tie-fix | 0–1999 | -0.01446 ± 0.00276 | 338/1434/228 |
| dcomp-nine | legal-tie-fix | 0-999 | -0.01246 ± 0.00369 | 153/733/114 |
| dcomp-nine | legal-tie-fix | 1000-1999 | -0.01646 ± 0.00409 | 185/701/114 |
| dcomp-ten-fast | legal-tie-fix | 0–1999 | -0.01471 ± 0.00328 | 430/1247/323 |
| dcomp-ten-fast | legal-tie-fix | 0-999 | -0.01477 ± 0.00449 | 211/632/157 |
| dcomp-ten-fast | legal-tie-fix | 1000-1999 | -0.01465 ± 0.00478 | 219/615/166 |
| dcomp-ten-fast | dcomp-nine | 0–1999 | -0.00025 ± 0.00174 | 128/1747/125 |
| dcomp-ten-fast | dcomp-nine | 0-999 | -0.00230 ± 0.00257 | 75/866/59 |
| dcomp-ten-fast | dcomp-nine | 1000-1999 | +0.00181 ± 0.00235 | 53/881/66 |

nine自身との比較は全件同点（0%、0/2000/0）。各runは2000件・WA0、記録あり。通常2000件のten対nineの差は2SEに届かず、この比較では10候補目の得点増分を確認できなかった。

| 解法 | judge平均(s) | argon比 | p99(s) | 最大(s) |
|---|---:|---:|---:|---:|
| argon-des-perf-latew105 | 1.630006 | 1.00000 | 1.798413 | 1.948920 |
| legal-tie-fix | 1.782543 | 1.09358 | 1.960380 | 2.089559 |
| dcomp-nine | 1.772792 | 1.08760 | 1.940552 | 2.125578 |
| dcomp-ten-fast | 1.750662 | 1.07402 | 1.941841 | 2.069254 |

| ten-fastの対応差 | helper_end(ms) | req(ms) | judge(ms) | p99差(ms)、paired bootstrap 95%区間 |
|---|---:|---:|---:|---|
| vs legal-tie-fix | -27.68 ± 1.07 | -2.33 ± 0.63 | -31.88 ± 1.51 | -18.54 [-59.98, -2.25] |
| vs dcomp-nine | -20.70 ± 1.08 | -0.51 ± 0.66 | -22.13 ± 1.52 | +1.29 [-33.64, +20.01] |

p99の区間は同じseedを組で再抽出した4000回bootstrap。最終比較の外部負荷は平均0.137 core、最大0.550 core。

ten-fastのend_secは平均1.544045s、p99 1.711994s、最大1.852230s。1.8/1.9/2.0s超は2/0/0件。時刻による処理変更なし。全2000件で完成候補数は10。候補9を選んだのは255件。

### 未見500–999・8列の追加確認

基準nineの`20261108-115455_legal-tie-fast`と、ten-fastの保存設計を同じlegal-tie-fastで再生した`20261108-124817_legal-tie-fast`を比較した。凍結後の確認で、結果を設定選択に使っていない。実列0は通常比較と500/500一致。

| 注文列 | 差 (%) | 差 (moves/order) | 勝/分/敗 |
|---|---:|---:|---:|
| 新規1–7 | -0.00330 ± 0.00145 | -0.0003295 ± 0.0001448 | 37/440/23 |
| 全8列 | -0.00309 ± 0.00140 | -0.0003083 ± 0.0001403 | 40/439/21 |
| 実列0 | -0.00164 ± 0.00377 | -0.0001602 ± 0.0003789 | 33/440/27 |

新規7列でも10候補目の改善は2SEを超えた。

### 判定

10候補目を追加してもnineの設計時間以下に収まり、平均時間のargon比1.10以下も満たした。Task9の時間資金を作る目標を達成した。p99はlegal-tie-fixより18.54ms低く、nineとの差+1.29msは測定のばらつきの範囲だった。10候補目の小さな未見リスト利得と、出力同一の高速化を設計側の部品として渡す。候補数を増やさず時間余裕を残す用途にはdcomp-nine-fastも使える。
<!-- FINAL_END -->

## 再現と引き継ぎ

`task9_make.py`、`task9_window.py`、`task9_sparse.py`、`task9_bitlive.py`、`task9_pack.py`、`task9_colcost.py`、`task9_flags.py`、`task9_valid32.py`が個々の案を生成する。`task9_final_source.py`は採用した高速化と凍結ten-lateを組み合わせ、ソースの同一性をassertする。元のTask8ソルバは未編集。

`run.py`は標準`scripts/pahcer_run.py`を呼び、コンパイルにも共通flockとniceを付ける既存wrapper。solver binaryの直接実行はしていない。通常runは記録し、replayは標準仕様で記録対象外。重い集計も共通lock＋nice。共有ソース・trial_log・STATE・他の解法の手動編集はなく、commitなし。

```sh
/home/sato/ahc074/.venv/bin/python solutions/dcomp-notes/run.py \
  --compare solutions/argon-des-perf-latew105 solutions/legal-tie-fix \
  solutions/dcomp-nine solutions/dcomp-ten-fast --seeds 0-2000 --save-design \
  -c "Task9 frozen final"
```

`task9_finish.py`は同一性の前提を検査して凍結し、最終比較・集計・未見replayを順に実行する。`FROZEN9.json`が既にある場合は上書きを拒むので、再実行は上の個別コマンドを使う。集計は`task9_final_stats.py`、同一性は`identity.py`と`task9_candidate_check.py`。

設計側だけの差分は`solutions/dcomp-ten-fast/from-dcomp-nine.patch`。M1との統合は未実施であり、合成後の得点・時間は別途測る必要がある。短い実仕上げを選別段に使う任意実験には進まず、今回確認した部品を渡す。
