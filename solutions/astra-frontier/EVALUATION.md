# 評価の再現と前提

この研究は、`51d7f7b37de3c3c4346628572977db4ad1793d99` の
`solutions/astra-search4/main.cpp` を基準にする。基準ソースのSHA-256は
`8e268a0171efea5f2ed727d045e19f45236b84e1effcd20377933d8063812411`。

## 独立した入力

Python 3.12.14の標準`random.Random`で新しい2000ケースを生成した。
seedを`0xA07420261102`とXORし、各商品は64位置から32位置を一様に選ぶ。
256商品が重複した場合は引き直す。最初の注文は256商品から一様、
以後は直前の商品を除く255商品から一様に選ぶ。
これは公式`tools/src/lib.rs`と同じ分布だが、乱数生成器が違うので**公式seedとの対応はない**。
全入力のSHA-256は`cases-manifest.json`に残す。

入力末尾にある将来注文はテスターだけが読む。解法には設計前に商品一覧だけを渡し、
設計出力を受け取ってから注文を一つずつ送る。

## 共通の評価器

既存の`pahcer_run.py --compare`を変更せずに用いた。
`evaluate.py`はCPU並列数を4へ制限する薄い呼出し役である。
同じseedの候補を続けて実行し、開始する候補の順序をseedでずらす。
新規入力と既存入力のseed番号が異なるため、全て`--no-record`で実行して既存pahcer値へ混ぜない。

- GCC 13.3.0、`-std=c++23 -O2 -DCLOCK_SCALE=1.1`。
- 通常評価は提出用ソースそのもの。2秒超・WA・誤表示数を別に報告。
- 指標はケースごとの`100 log(候補スコア/基準スコア)`の平均と標準誤差。
- 絶対スコアは`384E+T`で小さいほど良い。E=0ならスコア/1024が注文あたりの手数。
- 標準誤差の2倍未満の差は、改善・悪化と確定しない。
- 64件の候補選定と、その後の未使用ケースによる固定候補の評価を区別する。
- stderr指標は値が存在するケース数`n`もJSONへ出す。欠損値を0で補完しない。

この環境にはRustがなかったため、公式State/interactの規則を移した
`portable_tester.cpp`を使用した。公式Rustバイナリを実行したとは扱わない。
小さい正常・誤表示・不可視操作・余計な出力・範囲外・EOF・クラッシュの7例を
独立な`scripts/replay.py`と照合し、評価でも全出力を可視性検査付きで再生する。

初期の逐次ファイル中継では、一部の保存stdout/stderr末尾が欠けた。
そのため現在のテスターは対話中のstdout/stderrをメモリへ保存し、
解法終了後に完全なログとして書き出す。対話の入力やスコアの規則は変えない。
固定仕事量の診断は完全出力方式で再実行し、全32出力のスコア一致を確認した。
本報告で最終判断に使う評価は、保存出力の再生一致を条件とする。

## 元の入力を置き換えずに再現する

元のリポジトリの`tools/in`は公式入力なので、生成したケースで上書きしない。
新しい評価用ディレクトリを作る。

```sh
# 元のcheckoutで実行。--outのディレクトリは存在していてはいけない。
python3 solutions/astra-frontier/prepare_workspace.py \
  --out ../ahc074-frontier-evaluation \
  --tester "$PWD/tools/target/release/tester"

# Rust版テスターがない環境では、上の--testerの代わりに--portable-testerを指定する。
cd ../ahc074-frontier-evaluation
python3 solutions/astra-frontier/evaluate.py \
  --compare solutions/astra-search4 solutions/astra-earlytable \
            solutions/astra-sparse12 solutions/astra-research-escape \
            solutions/astra-privategate \
  --seeds 1000-1500 --no-record -c 'frontier independent holdout'
```

`FRONTIER_WORKERS`で並列数を変えられる。通常は4。
比較中は他の重い計算を走らせない。反復回数でなく時間で探索を打ち切るため、
別環境で絶対手数が一致するとは限らない。必ず基準と候補を同じ評価で測る。
利用者が手元で測った10.45手/注文と、本報告の絶対値を直接比較しない。
この環境では前計算・設計の後に残る時間が違い、軽量な注文処理へ切り替える件数も変わる。

## 固定仕事量の診断

通常評価とは別に、設計の探索量を揃え、注文の途中で軽い処理へ切り替わらない診断を用いる。
これは2秒を超える場合があり、提出可能な成績とは別扱いである。

```sh
python3 solutions/astra-frontier/diagnostic_sources.py \
  --out runs/fixed-diagnostic \
  solutions/astra-search4 solutions/astra-structural-fast
MAP_ITERS=1000000 GOPT_STEPS=200000 ANNEAL_ITERS=20000000 \
CLIMB_ITERS=66000 DECODER_ITERS=42 \
python3 solutions/astra-frontier/evaluate.py \
  --compare runs/fixed-diagnostic/diag-astra-search4 \
            runs/fixed-diagnostic/diag-astra-structural-fast \
  --seeds 0-16 --no-record -c 'fixed design work, complete query planning'
```

診断用ソースは`kFastAfter`と`kHelperGiveUp`の期限だけを延ばす。
変換前後のSHA-256と変更した定数は生成時のmanifestへ保存する。
設計反復回数には既存の環境変数を使い、将来注文を設計へ渡す変更は行わない。

疎な12証人版の追加診断では、上と同じ環境変数で
`solutions/astra-search4` と `solutions/astra-sparse12` の診断コピーを作り、
生成seed160〜223の64件を `--compare --seeds 160-224` で比較する。
診断変換の記録は `fixed64-transform.json` にある。
