# ソースと証拠の対応

研究の比較基準は添付の eject-single-window。最新のesw-climb4との比較ではない。

## ソースの固定

| profile | 生成後SHA-256 |
|---|---|
| lean | `c83b4b8f4be0d1f0a4de0d182be723e2c9753c553329158f6373921a32a61c71` |
| research | `36df8ea1c276fd3431c78ce828947bb58b3a0377ab255b457decde4247879a1b` |
| wide | `9dc633371253fa14f9bbb91afc6bd8497948485fd9a7ca1085e46f3aefeb5c5c` |


`build.py` が基準・圧縮差分・生成後の全hashを検査する。GitHubには主3profileの基準と差分を置き、会話のソースZIPには生成した単一C++も入れる。不採用のtwo-caps profileはソースZIP側に保存し、その生成ソースSHA-256は `4a3faed770a33522f73382da51e88f5072d65210ea94a4b0e2bcf534a3c8c4fb`。
.gz差分はバイナリであり、base64文字列として保存するファイルではない。

## 評価時と配布時の違い

主比較の前半64件は初期研究版、後半64件は前回OLD_HELPERを統合した研究版による。最終配布版はさらに任意の区間DPキャッシュを追加したが、既定は無効。5設定×8件で全出力の同一性を確認した。lean版は主要変更だけを元ソースへ移し、最終既定変更前の8件・変更後4smoke実行・対話2実行でも保存出力との一致を確認した。全128件を最終の配布ソースで再実行したとは述べない。

`results/validation.json` は検査の総括、`results/paired128.csv` は主6方式のケース別手数、`results/comparisons.csv` は標準誤差付き集計、`results/experiments.csv` は探索段階の別案。
`results/input-hashes.json` は公式seedではない独自128入力のSHA-256。標準ライブラリのshuffle実装によって生成結果が異なる環境では、証拠ZIPのinputsを `evaluate.py --inputs PATH` へ渡す。

## 原出力アーカイブ

会話に添付する `ahc074-kbest-evidence.zip` には128入力・128設計・768 stdout/stderr・入力/出力/設計hash・評価時ソースの各版・最終smoke/対話結果を保存する。巨大な生出力をGitHubの通常差分には載せない。
すべての出力は独立C++チェッカーで検査し、原出力と集計のhashも照合した。公式Rust testerを使用した結果ではない。

## 時間と公平性

FIXED_WORKは設計後半の期限も無効化し、NO_FALLBACKは注文の簡易処理移行を無効化する。基準も候補も同一設計と全1024通常注文で比較する。設計仕事量固定の手数と提出の2秒成績は異なる。
`results/timing.json` は別の8件CPU測定の集計、会話のソースZIPに含む `results/timing-rows.json` は56個の記録。設計読込後の初期化と注文処理を含み、設計探索は除く。キャッシュが明確に速いとの主張はしない。

## 最新mainへの移植

最終確認mainは `21151b53e5ff0a34e0cd59323a36457a5a4dd5c4`。このPRは研究保存であり、現行のOP_TAG・DesignStore・effortを置き換えるものではない。採用判断には、現行mainへlean変更だけを移植し、通常のpahcer同時比較が別途必要。
