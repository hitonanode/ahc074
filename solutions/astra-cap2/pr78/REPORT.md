# AHC074: 固定紙を使う表示と、比較器の枠を広げる実験

## 結論

**最終的な継続候補は `solutions/astra-cap-as5/main.cpp`。作業中に追加された最新基準 `as5-g38` にも固定capを移植し、容量修正後の独立228件で −0.272% ± 0.102%、10.52626→10.49754手/注文を確認した。** 初期の別256件も−0.279% ± 0.100%で同じ方向だった。G37へ減らす版の優位は確認できず、G38の直接移植を優先する。詳細は末尾の追補。

当初指定された `astra-search4` を基準にした `astra-cap` の主実験は、通常の時間配分の独立512ケースで **−0.557% ± 0.074%** の平均log比だった。この512件は後述の一時配列容量修正前の評価で、修正後の固定32件は全出力が一致した。 平均は10.60873→10.54965手/注文、1ケースあたり約60.50手の減少。勝/分/敗は312/0/200、WA=0、誤表示E=0。点推定は0.5%を超えるが、約95%区間は改善側0.412〜0.702%であり、「最低0.5%の改善」を保証する結果ではない。

固定回数の544ケースでも −0.302% ± 0.052%（333/3/208）を確認した。時間配分とは別に構造の効果を確かめられた。一方、1枚で2〜3窓を扱う構成や一般印刷の各案には、現時点で採用に足る結果がない。

担当窓を列費用で選び直す `astra-cap-joint` も独立256件で −0.515% ± 0.117%だったが、固定窓版より良いという根拠は得られなかった。座標の共同最適化を足す根拠は得られなかったため、最新基準への移植も固定窓版に留めた。

このPRは研究結果の共有用であり、mergeや提出を推奨するものではない。比較対象はユーザー指定の `solutions/astra-search4/main.cpp`。元の解法と共通スクリプトには変更を加えていない。

## 1. 有望な構造: 持ち上げ位置で1窓を切り替える

専用紙を持ち上げる操作には、紙をどの深さへ置くかという自由度がある。これを表示の1 bitに使う。

`astra-cap` は物理窓63だけを黒く覆う固定紙を1枚追加する。汎用紙6枚・汎用窓36個は維持し、ハンドルを28→27個、専用紙を186→185枚にする。全256商品を覆うため、共有対は70→71組、単独紙は116→114枚となる。

共有対の2商品が固定紙の窓で異色なら、専用紙には白を印刷する。白の注文では専用紙を固定紙より上へ、黒の注文では固定紙の直下へ持ち上げる。同色の共有対と単独商品は、その色を専用紙へ印刷し、普通に上へ持ち上げる。いずれも通常の持ち上げ1手で済む。

### 成立する理由

固定紙は対象1窓以外すべて穴なので、専用紙をその下に置いても他の63窓には影響しない。汎用紙が固定紙を越えない条件を維持し、後処理にも同じ条件を追加した。以前の専用紙を補助紙として上に残す候補はあり、全候補で最終表示と各操作の可視性を検査する。最初に固定紙を上へ移す1手だけが必要で、それ以降は固定紙を動かさない。初期の汎用紙は対象窓がすべて穴なので、この最初の操作も合法である。

表示の1 bitを消したのではなく、既に必要だった専用紙の移動先に符号化した。既存のCAPWIN実験が汎用窓の整合条件を1つ除いたのに対し、この実装はハンドルから窓を外す。

主な変更だけ読む場合は [基準からcapへの差分](cap-changes.patch)、[capからcap-jointへの差分](cap-joint-changes.patch) を参照。提出用ソースは各ディレクトリの `main.cpp` で完結する。

### 得失

この操作自体に追加の注文別操作は要らないが、構造全体の得は自明ではない。固定紙に1枚使うため共有対を1組増やし、ハンドルが減ると列が長くなる。比較器の互換性、列の掘り出し、三角形の穴、共有対の穴、オンライン補助紙の相互作用を含めた実測が必要である。単純な列数の連続模型だけから改善を主張しない。

数理的な得失、2窓capの互換性、近距離対の通過率については [`../astra-cap/ANALYSIS.md`](../astra-cap/ANALYSIS.md) を参照。

### 担当窓の選び方

| 実装 | 追加した選択 |
|---|---|
| `astra-cap` | 物理窓63で固定 |
| `astra-cap-select` | 比較器の割り当て後、残る28座標から71対のmatching代理値が最小のcapを選ぶ |
| `astra-cap-joint` | 4区間の設計SAの間で、capと27ハンドルの交換を列・穴の `Design::cur` で評価し、次のSA区間で再調整する |
| `astra-cap-two` | 1枚のcapが2窓を覆う。共有対の投影が同じ、または片側がcapの模様と一致する場合だけ許す |

`cap-joint` の「厳密な再計算」は既存の設計モデルに関するもの。実際の1024注文を見て最適化しているわけではない。汎用窓は交換しないので、汎用互換表と距離表を保持できる。各候補で列の全共有対が新しいハンドルでも同色であること、列に白黒両方の紙が残ることを確認する。内部bitの交換と物理座標への対応表を同時に更新する。

## 2. 比較実験

すべて同一入力に対するpaired comparison。差はケース単位の `100*log(候補スコア/既存スコア)` の平均で、負が改善。`±` は標準誤差で、95%区間ではない。1ケース内の1024注文を独立な1024サンプルとは数えていない。

|条件・範囲|候補|N|既存→候補、手/注文|平均log比 ± SE|勝/分/敗|根拠|
|---|---|---:|---:|---:|---:|---|
|固定・0〜287|astra-cap|288|10.46749 → 10.42919|-0.366% ± 0.070%|180/0/108|[cap-development-288](results/cap-development-288.json)|
|固定・追加288〜543|astra-cap|256|10.45304 → 10.42927|-0.229% ± 0.079%|153/3/100|[cap-validation-256](results/cap-validation-256.json)|
|固定・追加288〜543|astra-cap-select|256|10.45304 → 10.42643|-0.256% ± 0.077%|152/2/102|[cap-validation-256](results/cap-validation-256.json)|
|通常・独立1000〜1255|astra-cap|256|10.61043 → 10.55339|-0.537% ± 0.110%|148/0/108|[cap-normal-holdout-256](results/cap-normal-holdout-256.json)|
|通常・独立1000〜1255|astra-cap-joint|256|10.61043 → 10.55573|-0.515% ± 0.117%|158/0/98|[cap-normal-holdout-256](results/cap-normal-holdout-256.json)|
|通常・追加1256〜1511|astra-cap|256|10.60703 → 10.54591|-0.577% ± 0.098%|164/0/92|[cap-normal-additional-256](results/cap-normal-additional-256.json)|
|通常・独立1000〜1511合計|astra-cap|512|10.60873 → 10.54965|-0.557% ± 0.074%|312/0/200|[cap-normal-holdout-512](results/cap-normal-holdout-512.json)|

0〜543の固定回数合計は [cap-fixed-combined-544.json](results/cap-fixed-combined-544.json) を参照。同じ凍結ソース・固定回数の重ならない544入力を結合した。通常512件の前半は3解法、後半は基準と固定capの2解法で、各ケース内では連続して対比較した。上表には部分集合と合計を併記しているため、行を足してケース数を数えない。

通常の絶対手数がユーザーの約10.45と異なるのは実行環境・時間による探索打切り量・生成入力が異なるため。比較は常に同じ環境・同じ入力の既存解法との差で行った。固定回数の基準は約10.46手/注文だった。

### 探索段階の結果

|実験・候補|件数|平均log比 ± SE|勝/分/敗|根拠|
|---|---:|---:|---:|---|
|astra-matching|32|+0.292% ± 0.215%|13/0/19|[screening-a](results/screening-a.json)|
|astra-novel|32|+0.043% ± 0.238%|16/0/16|[screening-a](results/screening-a.json)|
|astra-online|32|-0.011% ± 0.081%|17/1/14|[screening-a](results/screening-a.json)|
|generic-mdp|32|-0.007% ± 0.011%|15/6/11|[screening-a](results/screening-a.json)|
|astra-joint v1（initial.cpp、固定）|32|+3.504% ± 0.315%|1/0/31|[screening-b](results/screening-b.json)|
|astra-overlap|32|+0.024% ± 0.019%|7/17/8|[screening-b](results/screening-b.json)|
|astra-sparse-exact|32|+0.080% ± 0.225%|15/0/17|[screening-b](results/screening-b.json)|
|astra-nonlinear|32|-0.080% ± 0.051%|3/29/0|[screening-c](results/screening-c.json)|
|astra-rule2|32|+0.000% ± 0.000%|0/32/0|[screening-c](results/screening-c.json)|
|astra-rule-sweep4|32|-0.080% ± 0.051%|3/29/0|[screening-c](results/screening-c.json)|
|astra-rule-flex|32|-0.059% ± 0.055%|3/27/2|[screening-d](results/screening-d.json)|
|astra-rule-full|32|-0.075% ± 0.056%|4/26/2|[screening-d](results/screening-d.json)|
|staircase|32|+0.020% ± 0.014%|3/19/10|[screening-d](results/screening-d.json)|
|astra-cap-select|32|-0.147% ± 0.208%|16/0/16|[screening-f](results/screening-f.json)|
|astra-rule-stationary|32|-0.001% ± 0.001%|1/31/0|[screening-f](results/screening-f.json)|
|astra-rule-anneal|32|+0.000% ± 0.000%|0/32/0|[screening-f](results/screening-f.json)|
|astra-nonlinear|128|+0.022% ± 0.017%|4/119/5|[decoder-development-128](results/decoder-development-128.json)|
|astra-rule-post|128|+0.000% ± 0.003%|3/123/2|[decoder-development-128](results/decoder-development-128.json)|
|astra-joint v2（main.cpp、通常）|8|+1.106% ± 0.680%|2/0/6|[guided-joint-normal-smoke](results/guided-joint-normal-smoke.json)|
|astra-cap-two|32|+0.266% ± 0.229%|15/0/17|[cap-two-screening](results/cap-two-screening.json)|
|mixed|32|+0.667% ± 0.228%|11/0/21|[cap-width-screening](results/cap-width-screening.json)|
|triple|32|+2.598% ± 0.259%|1/0/31|[cap-width-screening](results/cap-width-screening.json)|
|astra-cap-joint|32|-0.235% ± 0.203%|18/0/14|[cap-joint-screening](results/cap-joint-screening.json)|
|astra-post-pair|32|+0.000% ± 0.000%|0/32/0|[screening-e-32](results/screening-e-32.json)|
|astra-post-balanced|32|-0.001% ± 0.001%|1/31/0|[screening-e-32](results/screening-e-32.json)|

試した候補が多いため、最初の32件の最良値だけで採用を判断しない。特に非線形印刷の最初の32件の改善は、追加128件で再現しなかった。

### 時間と正しさ

通常512件の固定capと基準、および通常256件のcap-jointについて、移植testerでWA=0・E=0。別の再生実装でも全操作の可視性と最終スコアの一致を確認した。

|通常run|N|平均実時間|最大実時間|2秒超|最大CLOCK_SCALE適用後end_sec|
|---|---:|---:|---:|---:|---:|
|astra-search4|512|1.6465s|1.7028s|0|1.85859s|
|astra-cap|512|1.6439s|1.6729s|0|1.83159s|
|astra-cap-joint|256|1.6454s|1.6870s|0|1.84441s|

詳細は [normal-timing.json](results/normal-timing.json)。通常比較のソースには時間打切り・fast-modeが残っている。上記の主比較中は固定窓版のsourceを変更していないことを、runの保存コピーとバイト単位で照合した。その後、最新基準への移植レビューで共有対71組に対して一時配列2個が70要素のままだと分かったため、全cap版で128要素へ拡張した。探索・費用・オンライン方策は変えていない。評価原版はcommit `4c5a24a87505d19bc1a69d82795e4fed86867062` に残る。容量修正後は固定32件で基準と候補を再評価し、capの全stdoutが修正前とバイト単位で一致した（`20261101-204700`、[capacity-fix.json](results/capacity-fix.json)）。最新基準に対する通常時間比較は末尾の追補に区別して記録する。

固定回数の実験は構造の効果を分離するための診断であり、2秒以内の性能とは解釈しない。通常の時間制限による探索量はこの環境で測ったもので、AtCoderの実機での時間保証ではない。

## 3. 比較器を一般の印刷へ広げる試み

既存の1窓2紙の白黒比較を、白黒両方を含む任意の三値印刷へ拡張した。6紙で非定数のルールは `3^6 - 2*2^6 + 1 = 602` 通りある。720順序に対する出力をbitsetにし、各商品の許容順序の積集合から可解性を判定する。方向付きの合法移動グラフで、許容順序集合から逆向きに距離を求めて費用を評価する。

底以外の汎用紙が見える性質を保つため、15種類の2紙比較をそれぞれ最低1窓残す。これにより、従来の合法移動グラフを使える。一般印刷を採用した場合も、専用紙の互換性判定・印刷・実際の経路・Interleaveの表示条件を一致させている。

次を別々に評価した。

- 均等色の140ルールで1窓ずつ改善する `astra-nonlinear`。
- 比較窓の固定を緩める `astra-rule-flex`、全602ルールの `astra-rule-full`。
- 実際に選ばれた70共有対を後段で守る `astra-rule-post`。
- 一様な720状態ではなく、実70対の最短移動policyから定常分布を計算する `astra-rule-stationary`。
- 悪化受理と2窓同時変更を入れる `astra-rule-anneal`。

定常分布は720状態のMarkov連鎖を反復計算し、加重popcountで候補を評価する。32件では有効状態数は平均約220で、一様ではなかった。しかしルール変更はほとんど増えず、実コストの改善もほぼなかった。今回の1窓近傍では、開始分布の補正だけで停滞は解消しなかった。

2窓SAの実スコア比較は均等色140ルールで32件×10000候補を調べた。悪化も許すSAで平均51候補を受理し、平均1.66回の2窓変更受理があったが、全32件で最良値は初期値を更新しなかった。単調な1窓探索だけを試して諦めた結果ではない。ただし、これで一般印刷全体の不可能性が証明されたわけではない。

合法性の専用チェッカーと模型の詳細は `astra-novel/graph-check.cpp`、`astra-nonlinear/check.cpp`、`astra-rule-anneal/check.cpp`、`astra-rule-stationary/REPORT.md` に残す。

## 4. 過去の否定を見直した三つ組の模型

従来の共通印刷と穴による共有模型では、3商品間で一つでも異なる窓を穴にし、3つの要求それぞれの汎用制約が可解である必要がある。3組のpairが互換というだけでは十分でない。

ランダムなM6/G36の比較器でtripleが0個でも、窓の割り当てを三つ組向けに学習すれば存在する構成を作れた。ただし、三つ組だけを増やすと残りのpair coverが悪化する。全256商品の表示と紙の予算を維持することが必要で、tripleの個数だけを成果とは数えない。

M8/G36で少数のtripleを学習する連続列模型には、同じ8枚比較器のpair構成に対して約0.07手/注文の改善余地があった。これは6枚の既存解法に対する改善ではなく、整数の列配置・実注文・実時間でも未確認である。比較器を8枚へ増やす費用を含めた優位性を示すには、さらに実装が必要。

再現コード、生成した構成と制約の検査、模型の詳しい数値は [`../astra-triple-probe/REPORT.md`](../astra-triple-probe/REPORT.md) に分けた。

## 5. その他の再検討

- **疎な比較グラフ:** 6紙のまま比較辺を減らし、表現の冗長性と移動距離を変える。隠れた紙を動かさないよう合法な遷移表を再構築。汎用操作だけは減ったが全体では優位を確認できなかった。`astra-sparse-exact` は設計評価も実際の合法距離へ合わせた対照実験。
- **matchingと窓の共同探索:** 70共有対を状態として持ち、窓変更と局所修復を同時に探索。第1版は大きく悪化。許容辺へ誘導する第2版でも、長い探索の代理値が既存に負け、全辺再構築に約93.4%の時間を使った。詳細は `astra-joint/EXPERIMENTS.md`。
- **重なる穴埋め:** 違う高さから始まる2紙の重なり、および最大4紙の段階的な重なりを探索。過去にも2紙の案は試されており、今回は現在の実装での再検討。明確な改善なし。
- **将来費用:** 列の同色連続に対する凸な評価、汎用720状態の相対価値反復を再評価。既存の1段先評価に対して有意な改善なし。小さい列MDPの理論上の改善幅も、全注文換算では小さかった。

## 6. 再現手順とファイル

Rustが使える環境では `--portable-judge` を外せば公式testerを利用できる。以下はこの実験で使った入力分布と固定回数の再現例。

```bash
python3 solutions/astra-lab/generate.py --count 2000 --out solutions/astra-lab/cases
python3 solutions/astra-lab/bench.py --portable-judge --threads 4 --input-dir solutions/astra-lab/cases --fixed 800000,200000,20000000,66000 --compare solutions/astra-search4 solutions/astra-cap --seeds 0-288 -c 'Reproduce fixed cap comparison'
python3 solutions/astra-lab/summarize.py BASE_RUN CAP_RUN --label reproduced-cap
python3 solutions/astra-lab/verify.py BASE_RUN CAP_RUN --processes 4
```

通常の時間配分で比較する場合は `--fixed` を外す。`--extend RUN... --seeds START-END` は同じバイナリで追加ケースを評価する。固定モードのrunを伸ばす際も、同じ `--fixed` を指定する。

### 測定条件

- 基準commit: `bb45c289d6672ecf410f9c004f3856178645739b`。基準C++のGit blob: `ac67aa4b7d7da8a71d6d85709c262977ea8dc22d`。
- GCC 13.3、C++23、`-O2 -DCLOCK_SCALE=1.1`、4並列。
- 固定回数: `MAP_ITERS=800000`、`GOPT_STEPS=200000`、`ANNEAL_ITERS=20000000`、`CLIMB_ITERS=66000`。annealはバッチ境界により実際は20000768回。
- 固定モードでは測定用コピーだけでhelper構築打切りとオンラインfast-modeを無効化した。提出用C++の時間制限処理は変えていない。
- 入力はPython `Random(74000000 + case)`。公式と同じ分布だが、同じ番号の公式ChaCha20入力とは一致しない。既存の `tools/in/` を上書きする必要はない。
- 未知の未来注文はsolverに送らない。最初は商品一覧だけを送信し、注文は1つずつ対話させる。
- この環境にはRustがなかったため `tools/src/lib.rs` から移植したC++ testerを使い、既存 `scripts/replay.py` でも独立に再生した。公式Rustバイナリそのものを実行した結果ではない。
- 初期の非atomic出力によるpilotでは途中のstdout/stderrが記録に混じったため採否から除外した。現在のadapterは終了した対話をメモリからatomic renameで公開し、スコア・stderr・再生・1024注文の一致を検査する。

`results/*.csv` に各ケースのE/T、実行時間、比較差、入力と出力のSHA256を、対応するJSONに平均・標準誤差・勝敗・run-idを保存した。`results/input-manifest.json` は全生成ケースのseed対応とhash、`results/protocol.json` は測定条件と検証記録。入力本体・実行バイナリ・巨大な生ログはPRに含めない。

## 7. 作業中の基準更新と容量修正後の追補

mainへ `as5-g38` が追加されたため、同じ固定1窓capを最新基準にも移植した。`astra-cap-as5/main.cpp` はG38/H25の直接移植、`g37.cpp` はG37/H26として最新基準と同じ列数を保つ版。基準C++ blobは `b9cff3591c88d6d4c8af8f5702a62061bacc6539`。

共有対を71組へ増やしたため、一時配列 `empty` と `saved` を70要素から128要素へ拡張した。旧版でクラッシュ・不正操作は観測されなかったが、過去の配列アクセスを計装して監視した結果ではない。修正後の固定32件では、基準とcapの両方が旧runと全stdout一致し、capのスコアも全件一致した。現在の全capソースには容量修正を適用している。

移植の4件smoke（1512〜1515）は正常終了。容量修正前の追加256件（1516〜1771）では、G38/H25が−0.279% ± 0.100%（149/1/106）、G37/H26が−0.187% ± 0.101%（145/0/111）だった。この段階の結果は初期調査として区別し、最終判断は修正後の独立ケースによる。[初期比較のJSON](results/cap-as5-before-capacity-256.json)

容量修正後の独立228件（1772〜1999、`20261101-204849_*`）は次の通り。3解法ともWA=0、E=0。既存replayの独立再生でも、全684出力の操作の可視性と得点一致を確認した。

|構成|平均手/注文|最新as5-g38比 ± SE|勝/分/敗|最大実時間|
|---|---:|---:|---:|---:|
|as5-g38|10.52626|+0.000% ± 0.000%|0/228/0|1.6603s|
|astra-cap-as5|10.49754|-0.272% ± 0.102%|125/0/103|1.6642s|
|g37|10.51879|-0.071% ± 0.104%|114/1/113|1.6664s|

[修正後の集計JSON](results/cap-as5-corrected-holdout-228.json)、[ケース別CSV](results/cap-as5-corrected-holdout-228.csv)、[時間](results/cap-as5-corrected-timing.json)、[as5-g38からの差分](cap-as5-changes.patch)。G38版は約95%区間でも改善側だが、0.5%改善に届く結果ではない。G37版は標準誤差の2倍に届かず、優位とは判断しない。

最新基準向けの続きは `solutions/astra-cap-as5/main.cpp` を出発点とする。次の小さな候補は、cap座標交換で不適合になる共有紙1〜2枚を別列の単独紙と交換して修復する近傍である。今のcap-jointが許す「同じ列の全共有対が新handleでも同色」という制約を緩められるが、未実装・未検証の仮説。複数capや三つ組の全面移行より、まずこの可解性を守る小さい近傍と現在の構造の相性を測る方が具体的である。
