# final-time-pace（最終版: 時間で決める設計 + 注文処理のペース配分 + zero-init の修正）

改良元: `solutions/dcomp-combo-dual30`。次の 3 つの部品を合わせた。各部品の中身は、それぞれの README にある。

## 部品と出どころ

- **設計: `solutions/dcomp-time-target`（Astra の Task 13）。**
  - 設計の探索回数を、設計開始からの絶対期限で決める。全設計の予算は 1.22 秒（倍率込みの時計）。
  - LOCAL_BENCH だけで使える切り替え（どちらも環境変数）:
    - `DESIGN_FIXED_ITERS=1`: dual30 の固定反復に戻す（同一性の検査用）。
    - `DESIGN_SECONDS`: 予算を変える。
- **注文処理: `solutions/jflags-pace-dual30`。**
  - 注文ごとに、残り時間から手間（6 段。5 は軽い計画）を選ぶ Pacer。
  - ペースの目標は 1.88 秒。最後の手段として、残りを全部軽い計画にしても 1.92 秒までに終わるうちだけ、重い手間を使う。
  - LOCAL_BENCH では手間を 0 に固定する（通常の比較を変えないため）。試験用のマクロ:
    - `PACE_SIM=f`: Pacer を有効にし、注文処理の段の時計を f 倍にする（f = 1.0 で、ジャッジと同じ動き）。
    - `PACE_SIM_START=t`: 注文処理が t 秒から始まったことにする。
    - `PACE_FORCE=e`: 全注文を手間 e で処理する。
- **zero-init の修正: `solutions/jflags-zinit-dual25/from-dual25.patch`。**
  - ジャッジの `-ftrivial-auto-var-init=zero` は、初期化子のない自動変数を毎回 0 で埋める。頻繁に呼ばれる作業用の配列（書いてから読むもの）に `NOINIT` を付けて、これを止める。Clang では `[[clang::uninitialized]]`、GCC では `__attribute__((uninitialized))`。
  - この flag のないビルドでは、出力も速さも変わらない。

## 作り方

1. `git merge-file -p solutions/jflags-pace-dual30/main.cpp solutions/dcomp-combo-dual30/main.cpp solutions/dcomp-time-target/main.cpp` で 3 方向に合わせた（衝突なし）。
2. `from-dual25.patch` を `patch -p1` で当てた。31 塊のうち、目次の 1 行の塊だけ当たらなかったので、手で足した。目次は段の目印と一致する。
3. 冒頭の説明の「注文処理は変えない」という 1 行を、ペース配分の説明に直した。

stderr の指標は各部品のもの（設計の `dt_<段>_*`・`design_time_*`、注文処理の `pace_*` など）。
