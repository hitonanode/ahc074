# final-time-pace 独立コードレビュー（Astra）

開始: 2026-11-09 02:49 JST。終了: 03:56 JST（締切04:30 JSTより前に完了）。
対象: `solutions/final-time-pace/main.cpp`（11,777 行、600,007 bytes）。
SHA-256: `8d64d7949f56f0eeb8e36b9b1d07b95fae5108e4f6194fb03b995d0479edc90b`。

提出条件の Clang、`LOCAL_BENCH` なし、`CLOCK_SCALE=1.0` を重点的に確認する。既存ファイルは変更せず、他のレビュアーの記録は参照しない。スコアの改善提案は対象外。

本番経路のClangビルドは公式2000入力すべてWA・表示誤り・手元での2秒超過が0件。指摘は未定義動作2件で、うち1件は追加のlibc++境界検査で停止を再現した。指定された通常のジャッジビルドでの停止や誤答を再現したという報告ではない。

## 指摘（重大な順）

### 1. 最下段の同位置移動で std::array の範囲外添字を使う

- **場所:** `solutions/final-time-pace/main.cpp:7318`（`Solver::shift_byte`）。呼出し元の7612行と7770行は同位置の移動を除外していない。
- **問題:** `p == dest == 191` では `std::memmove(&o[192], &o[191], 0)` となる。コピー長が0でも `std::array<uint8_t,192>::operator[](192)` の事前条件に違反する。`std::array` の添字はサイズ未満である必要がある。[C++23 sequence requirements](https://timsong-cpp.github.io/cppwp/n4950/sequence.reqmts)
- **具体例:** seed 503、注文1（0始まり）の後処理で `p=191, dest=191` に到達し、libc++ の境界検査がプロセスを停止する。要求された注文の出力が完了せず WA になる。
- **根拠（実行で再現）:** 未変更の本番ソースに `-D_LIBCPP_HARDENING_MODE=_LIBCPP_HARDENING_MODE_DEBUG` を加えた `20261109-031300_final-time-pace` は seed 503–522 の20件すべて停止。検証コピーで値と注文番号だけを出した `20261109-031519_review-astra1` も20件停止し、seed503の stderr に上記の値と直後の array assertion がある。冒頭に同位置の early return を足した `20261109-031519_review-astra1-2` は同じ20件すべて WA/E 0。コマンド条件は各 meta.json と `libcpp_debug20.log`、`shift_fix20.log`。
- **重大度:** 未定義動作。検査付き libc++ では **crash / WA**。指定されたジャッジ用の通常ビルドでクラッシュした証拠はなく、0 byte のため範囲外のデータ転送が発生するという指摘ではない。
- **最小修正:** `shift_byte` の先頭に `if (p == dest) return;` を追加する。検証用コピーの `REVIEW_FIX_SHIFT` がこの1行だけの修正を選べる。

### 2. 2次元の固定表を1行目の要素ポインタから行をまたいで読む

- **場所:** `solutions/final-time-pace/main.cpp:10536`（`deval::samples_for`、ポインタ作成は10533行）。
- **問題:** `&kBasis25[0][0]` は25要素の最初の内側配列を指す。それを `basis[(b+1)*H+j]` として150要素の平坦な配列のように使っている。31/35列の表も同じ。外側の表全体が連続配置でも、内側配列の範囲を越えるこのポインタ演算・読み出しはC++23で定義されない。[C++23 expr.add](https://timsong-cpp.github.io/cppwp/n4950/expr.add)
- **具体例:** 通常の `H=25`、最初の候補のV計算で `i=1,j=1,b=0` になると `basis[26]` を読み、25要素の行を越える。特別な入力を必要としない。実際のビルドで値が壊れたという再現はない。
- **根拠（コードと規格上の推論）:** 同じ表と式を抜き出した `basis_constexpr.cpp` を `flock -x /home/sato/ahc074/runs/.lock nice -n 10 clang++ -std=c++23 -fsyntax-only solutions/review-astra1/basis_constexpr.cpp` で定数評価させると境界違反で拒否される（`basis_constexpr.log`）。これは提出プログラムがクラッシュする再現ではなく、配列の範囲を示す補助検証。
- **重大度:** **minor（標準上の未定義動作）**。指定ビルドでの誤答・クラッシュは未確認。
- **最小修正:** 表を `kBasis25[row][j]` / `kBasis31[row][j]` / `kBasis35[row][j]` と2つの添字で読む小さなアクセサにするか、表自体を初めから一次元で宣言する。

## 確認範囲と検証

- 問題文と公式テスターの設計・移動・終了条件を確認した。
- 対象ソースのハッシュと段の目次を確認した。
- 通常経路と emergency 経路の設計・注文出力は改行と flush があり、注文入力の失敗または `-1` で直ちに return する。通常経路では紙番号と窓の置換も設計出力と操作出力で対応している。
- `steady_clock`、起点の一貫性、提出時の CLOCK_SCALE 既定値 1.0、絶対期限名の対応を確認。時間進捗の分母は下限付きで、段に入った時点で期限を過ぎていれば最初の反復前に終了する。
- Pacer の推定式は通常の単調な時刻では正かつ有限に保たれる。重みの分母・平方根・effort の添字に0除算や負値は見つかっていない。I/O と注文待ちは次の周期の `trip` に含まれる。
- NOINIT の全宣言について、読み出す範囲が書き込み済みであることを追跡した。対象は窓割当用配列、焼きなまし用6列バッファ、確率勾配の prefix/suffix、next-cost のキー・部分初期化配列、ColumnTops、filler-chain pool、canonicalize、後処理の ord/cover、ejection の所有窓と位置、neutral の first/second/third/pool。部分初期化は個数・有効 prefix・世代番号・マスクで保護されている。
  - 各宣言の行番号、容量、初期化と参照範囲の根拠を `noinit-audit.tsv` に記録した。検査で指摘1を避けるearly returnを選んだ場合も、これらの初期化方式は変更していない。
- Clang の radix 7+10 bit / GCC の 8+9 bit、Clang の next-colors、prefix replay 無効化、screen 成功時の link 構築省略を確認。最後の cap と表示の検査が残ることも確認した。
- FillerList の inline/heap 切替、canonicalize の unsigned 世代番号の周回、MDP の長さ・状態数上限、32/64 bit のビット列、Hungarian の有限対角コスト、候補を出力する前の可視性・表示・枚数の検査を確認した。
- Comparator の720状態・距離・可視性制約、PosetSums の固定表、設計初期化の両色確保と再試行、後処理中の vector とキャッシュの参照寿命、同一注文内でのメモの世代とキーも確認した。上記の配列添字2件以外に新たな問題は見つかっていない。

### 実行記録

- `20261109-025050_final-time-pace`: Clang 18 + libc++、`-O2 -march=native -ftrivial-auto-var-init=zero`、LOCAL_BENCH/CLOCK_SCALE 未定義。seed 0–49、50件、WA 0、E 0、実時間最大1.747秒、end_sec 最大1.717秒。
  - seed 220–499 と50–219を追加し、0–499の計500件。WA/E 0、実時間最大1.874秒、end_sec 最大1.828秒。追加評価の外部負荷はそれぞれ平均0.18/0.16・最大0.71/0.28コア。
- `20261109-025050_final-time-pace-2`: GCC 13、上と同じ提出経路。seed 0–49、50件、WA 0、E 0、実時間最大1.820秒、end_sec 最大1.779秒。コンパイラの警告は未使用変数のみ。
- 未変更のClang本番ソースの残りも、`20261109-033212_final-time-pace`（seed500–999）、`20261109-033327_final-time-pace`（1000–1499）、`20261109-033548_final-time-pace`（1500–1999）で各500件を確認。いずれもWA/E/2秒超過 0。実時間最大は順に1.756/1.750/1.764秒、end_sec最大は1.753/1.747/1.761秒。前記seed0–499と合わせて公式2000入力すべて正常だった。各評価の外部負荷は平均0.15/0.11/0.12・最大0.39/0.43/0.31コア。ジャッジでの時間を保証する結果ではない。
- `20261109-025140_final-time-pace`: Clang + libc++、ASan/UBSan、本番経路。初回 seed 50–69 は全件正常な注文出力を終えた後に環境の ptrace 制約で LeakSanitizer が終了失敗した。ソースの不具合とは扱わない。`ASAN_OPTIONS=detect_leaks=0` にして同じバイナリを seed 70–99 に extend し、追加30件はWA 0、E 0、ASan/UBSan検出なし。元の `--no-record` は extend に引き継がれる（extend は明示的な `--no-record` を受け付けない）。
- コマンドとコンパイラ警告は `prod50.log`、`sanitizer20.log`、`sanitizer30.log`。ビルド条件の切替はこのディレクトリの `run.py` から既存の `scripts/pahcer_run.py` を利用した。ビルドは共有ロックと nice、ケース実行は既存の評価ロックに従う。
- `20261109-025517_review-astra1`: 検証用コピー、Clang ASan/UBSan、effort 0 固定、seed 103–112 の10件。各注文を独立再生し、可視性・操作数上限・表示・内部順序・filler 状態を assert。さらに POST_MEMO_CHECK、SCREEN_REPLAY_CHECK、SCREEN_LINK_CHECK、SCREEN_CHECK、NEXT_PREFIX_CHECK、PARTIAL_MDP_CHECK、EJECT_GEOM_CHECK を有効化。WA/E/検出 0、screen_checked 合計9,299,123、screen_mismatch 0。強制最大探索と sanitizer により実時間4–5秒かかるが、これは提出のTLEの再現ではない。評価外負荷の警告もあるため時間の判断には使わない。
  - effort 1–5 を各10件（seed 170–219）追加し、全6レベル各10件、計60件でWA/E/assert失敗 0。screen_checked 合計31,860,635、screen_mismatch 0。
- `20261109-033851_review-astra1`: effort0固定・同じ参照照合群に、libc++ debug、float-divide-by-zero / float-cast-overflow、指摘1の最小修正を加えてseed825–1024の200件を検査。WA/E/ASan/UBSan/assert失敗 0、screen_checked 184,995,124、screen_mismatch / plan_failures 0。計装により4–7秒かかるため、本番の時間の評価には使わない。
- `20261109-025700_review-astra1` / `20261109-025700_review-astra1-2`: seed 116–165 の各50件、Clang、本番経路、PACE_SIM=2.0 / 5.0。注文段だけの時計を2倍/5倍へ伸ばした検査。どちらも WA/E 0。仮想 end_sec 最大1.88470 / 1.89037秒、ローカル変数の破棄後も最大1.88520 / 1.89170秒。実際のジャッジ速度の測定ではない。
- `20261109-030113_review-astra1`: `gen_inputs.py` の有効な偏った入力20件（近いバーコード群、固定窓、相補ペア、4窓ごとの2黒、2注文の交互反復）。WA/E/assert失敗 0、実時間最大1.872秒。うち2件は緊急設計。通常経路18件の end_sec 最大1.86852秒。入力はこのディレクトリの inputs/ に保存し、meta.json に出所を記録した。公式の一様乱数 seed としてのスコア比較には用いない。
- MSan はシステムの非計装 libc++ と組み合わせると入力 string、to_string の戻り値、文字列連結、ostream の内部で誤検出する。`20261109-025347_final-time-pace`、`20261109-025625_review-astra1`、`20261109-030530_review-astra1`、`20261109-031117_review-astra1` はこの制約のため安全性の検証とは扱わない。
- `20261109-031735_review-astra1`: 既知の文字列境界の shadow を補正し、文字列・iostream と外部 interceptor を除外した限定的な MSan 検査。seed773–775をPacer付き、796–798をeffort 0 固定で実行し、計6件でWA/E/MSan/assert失敗 0。NOINIT 数値バッファの確認を補うもので、除外したライブラリ経路全体を検査できたとは主張しない。強制探索とMSanで6–23秒かかり、提出の時間を示すものではない。
- `20261109-033252_review-astra1`: 同じ限定的MSan検査をseed819–824の6件で行い、effort間の全36遷移を72注文周期で強制した。WA/E/MSan/assert失敗 0。effort変更によって残る状態の初期化も確認した。
- `20261109-033918_review-astra1` / `-2`: H=31/35の再試行用構成で同じ限定的MSanと全36 effort遷移を実行。seed1025–1027の各3件でWA/E/MSan/assert失敗 0。数値バッファについての検査であり、除外した文字列・iostreamやジャッジの速度を検証するものではない。
- `20261109-031519_review-astra1-2`: 指摘1の1行修正を選んだ検証コピーで、libc++ debug 境界検査と操作列の独立再生を有効化。最初の20件にseed 523–772の250件（effort 0 固定）を追加し、計270件でWA/E/assert失敗 0。指摘1以外の標準ライブラリ事前条件違反は検出されなかった。
- `20261109-031851_review-astra1` / `-2` / `-3`: seed776–795の各20件、ASan/UBSan/libc++ debug、effort 0固定、操作列の独立再生。初期Gだけを32/28へ変更した前二者は全件H=31/35を通った。設計予算を0.001秒にした第三の検査では全件anneal_iters=0で、期限切れと再試行を通った。いずれもWA/E/検出 0。故障を想定した検査用設定で、提出のスコア・時間の比較には用いない。
- `20261109-032409_review-astra1`: GCC、ASan/UBSan、libstdc++ assertions、effort0固定と前述の参照照合群、seed799–818の20件。WA/E/検出 0、screen_checked 18,284,394、screen_mismatch 0。GCCで有効になるprefix replayを含む。
- `20261109-032906_final-time-pace`: 未変更のClang本番ソースに、変化する窓の数を24–63へ制限した有効入力120件を与えた。G=38が3件、G=32への再試行が35件、緊急設計が82件。WA/E 0、実時間最大1.877秒。初期化失敗後の通常経路・緊急経路も実入力で通った。
- `20261109-034019_final-time-pace` / `-2`: 未変更ソースのCLOCK_SCALEだけを1.35 / 2.0にしたClangビルド、seed1028–1077の各50件。固定量の設計処理も含めて時計を伸ばした検査で、WA/E 0。倍率込みのhelper_end_sec最大1.25897 / 1.32510秒、end_sec最大1.87991 / 1.88438秒。実際のジャッジで負荷をかけた測定ではない。
- Clang static analyzerも実行（`analyzer.log`、診断の経路は `/tmp/review-astra1-analyzer.plist`）。4警告は、非0のclzの戻り値を未制約として扱った負シフト、Hの上限35を考慮しない64ビットシフト、変更されない環境変数の2回目のgetenvがnullという仮定、未使用代入。実際の入力と本番設定で到達する指摘にはならなかった。
- Clang18で `-O2 -march=sapphirerapids -stdlib=libc++ -ftrivial-auto-var-init=zero -fstack-usage -c` のコンパイルも成功（`sapphire_build.log`）。最大の単一スタックフレームは465,928 bytes、mainは370,616 bytes。対象コードに無限再帰や深い再帰はなく、確認した呼出し関係でもスタックの急増は見つかっていない。AVX-512の実行はしていない。

`main.cpp` は対象のコピーに、`REVIEW_FORCE=0..5` による手間固定、`REVIEW_CHECK=1` による操作列の独立再生・内部状態の一致検査、ローカル変数の破棄後の時刻出力を足した検証用。REVIEW_MSAN のビルドだけ入力文字列の shadow を補正し、非計装 libc++ による interceptor の検査を抑止する。元ソースは変更していない。

## 検証の限界

- Clang21/GCC15、Sapphire RapidsのAVX-512、LTO+lldの実ジャッジ環境は手元にない。手元のタイミングからジャッジのTLEがないと保証することはできない。固定量の設計段は有限だが期限による中断はなく、注文の途中でも時計を読まないという構造は残る。それが1.93秒を越す具体的な本番入力・通常の速度変動を今回の検証では再現していないため、独立した不具合としては報告していない。
