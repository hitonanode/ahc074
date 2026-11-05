改良元: solutions/esw-clean

設計の各段の結び付きと、順序・目的関数・cap の選択を調べる研究用ディレクトリ。
`main.cpp` は分析器が使う比較元の無変更コピー。

`inspect.cpp` は保存設計から、窓割当の貪欲ペア、設計初期化のペア、最終ペアの重なりを調べる。
汎用窓を固定して残り26窓のどれを cap にするか選ぶ場合の、割当の目的値の変化も数える。
`--moves` では初期化直後と最終状態の単一窓変更を列挙し、壊れる対の数と、対・列を保持したモデル費用を測る。
解法やテスターは実行せず、保存設計と公開された商品一覧だけを使う。

分析は評価と同じ `runs/.lock` の共有ロックを取得して、評価と重ならないように実行する。
結果と実験の採否は REPORT.md、実行結果はこのディレクトリ内の JSON とログに保存する。
対話解法の候補は `solutions/design-frame-*` に置き、評価は `scripts/pahcer_run.py` で行う。
既存のログ・CLOCK_SCALE・LOCAL_BENCH・DesignStore・属性と操作ラベル・実験設定は維持する。

道具：

- `run_inspection.py --run RUN --seeds 0-200 [--moves] --output FILE`：保存設計の分析。省略時は `20261105-080311_esw-speed`。
- `summarize.py RUN ... --seeds 0-200 [--identity] --output FILE`：記録したスコア・段別の時間・出力の一致を集計。
- `build_variants.py`：この研究の候補を esw-clean から再生成する。生成先の自分のソースとREADMEを上書きする。
- `bin/g++`：pahcerのコンパイルも評価と重ならないように、共有ロック内でコンパイラを呼ぶ。

コンパイルと解析、各候補の設定・指標の詳細は `REPORT.md` と各候補のREADMEを参照。
