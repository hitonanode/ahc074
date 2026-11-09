# ia-static-config

改良元: `solutions/dcomp-combo-dual30`。

要求探索のSearchConfigと、直接search_envを読む中立探索の設定を、dual30の環境変数未指定時と同じコンパイル時定数へする。`IA_STATIC_CONFIG=1`（この試作の既定）ではconstexpr lookup/get/numberとconstexpr Configを使い、使わない分岐の削除を促す。`=0` なら親のF3_*環境変数と初期化をそのまま使える。設計の環境変数は変えない。

元の特別な既定値（NS_ALTERNATE=1、gap=1.0、NS_ROUNDS=3、NEUTRAL_SLACK=.30、PLAN_LIMIT=2、REPEAT_MIN=.05、POST_CANDIDATES=6、NEUTRAL_WIDTH=6）をすべて維持する。その他の設定・modeによる既定値・Clangだけprefix=0も親の初期化式をそのまま使う。浮動小数の既定文字列は対応するC++ literalを返す。候補・探索回数・費用式・時計・ラベルを変える意図はない。

既往: `deval-fixedcfg` は旧deval-vbranch-o3で全SearchConfigを固定した試行。今回はdual30でALT・追加親・whole-post memoなどの分岐が増え、最終ビルドもClang/libc++/LTO/zero-initになったため、旧GCC試験をそのまま転用せず一度だけ比べ直す。NOINIT属性とは別の変更。正確な既定挙動と速度は、各コンパイラ内のstdout完全一致と対応時間で確認する。
