# Astra 独立レビュー用

対象（改良元）: `solutions/final-time-pace/main.cpp`。

スコア改善は行わず、最終提出の不具合を調べるための記録と検証用ファイルを置く。対象ファイルや既存の共通ファイルは変更しない。結果は `report.md` に随時記録する。

検証は `scripts/pahcer_run.py` の処理を利用し、`--no-record` を指定する。コンパイル時のフラグを切り替える場合も、記録と評価ロックを維持する。バイナリは `runs/` または `/tmp` に置く。

- `run.py`: `solutions/jflags-notes/run.py` を元にした起動用コード。`JFLAGS_ARMS` で渡したコンパイラとフラグをそのまま使い、LOCAL_BENCH / CLOCK_SCALE を自動で加えない。ビルドは共有 lock と nice を使い、ケースの実行は既存スクリプトの lock に従う。`REVIEW_INPUT_DIR` があれば入力とその再生だけを指定ディレクトリへ切り替え、出所を meta.json に記録する。
- `main.cpp`: 対象ソースの検証用コピー。`REVIEW_CHECK=1` で各注文の操作列を独立に再生し、可視性・個数・表示・内部順序・filler を検査する。`REVIEW_FORCE=0..5` で努力レベルを固定し、`REVIEW_FORCE=cycle` でレベル間の全36遷移を72注文ごとに通せる。ローカル変数の破棄後に `review_after_locals_sec` を出す。
- `REVIEW_SHIFT_DIAG`: 最下段の同位置移動で注文番号・位置を出す。`REVIEW_FIX_SHIFT`: `shift_byte` に同位置の early return を加える。検査対象で見つかった境界違反の最小修正を確かめるためのもの。
- `REVIEW_INITIAL_G=32/28`: 再試行用の31/35ハンドル構成を直接使い、配列容量を検査する。`REVIEW_DESIGN_SECONDS=0.001`: 設計段の期限が既に過ぎている場合の初期化を検査する。通常の解法として比較・採用する目的ではない。
- `REVIEW_MSAN`: 非計装のシステム libc++ による誤検出を切り分けるため、入力文字列と `to_string` 戻り値の shadow を補正し、外部 interceptor の検査を抑止する。`msan.ignore` と組み合わせる検査は文字列・iostream の安全性を保証するものではなく、数値バッファの読み出しを対象とする。
- `gen_inputs.py` と `inputs/`: 有効だが偏った入力20件。緊急設計、一定色の cap、相関の強い窓、交互注文を試す。公式 seed のスコアとして比較しない。
- `gen_variable_inputs.py` と `inputs_variable/`: 変化する窓を24–63個に制限した120件。通常ソースの再試行・緊急設計を実際に通すための有効入力。
- `basis_constexpr.cpp`: 対象にある2次元表と平坦な添字を抜き出し、行を越える演算をコンパイラの定数評価で検査する。コンパイル失敗が期待される。
- `noinit-audit.tsv`: 各NOINIT宣言の行番号と、初期化範囲・参照範囲・容量上限の確認記録。
- `sapphire_stack.txt`: Clang18によるSapphire Rapids向けコンパイルのスタック使用量。実行できない命令セットのバイナリは作業用の `/tmp` に置き、このディレクトリにはテキストだけを保存した。

実行済みのコマンド条件・ソースは各 run の meta.json / src/ に保存される。`--extend` は明示的な `--no-record` を受け付けないため、元の no-record run から設定を引き継ぐ。
