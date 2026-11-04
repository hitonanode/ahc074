# 設計の模型と実際の手数の突き合わせ（label-audit）

改良元: なし（解法ではなく、分析のスクリプトだけを置く。main.cpp はない）

solutions/esw-roles の run（stderr に `@paper` / `@ops` を出す解法。子孫でもよい）を読んで、実際の手数を操作のラベルと紙の属性ごとに数え、設計の模型（main.cpp の `// ==== Design: units, columns and the cost model ====`）の項と並べる。

## audit.py

`python3 solutions/label-audit/audit.py RUN [--seeds 0-2000] [--procs 8] [--dump out.json]`

runs/ の出力を再生し（scripts/replay.py）、次を表にする。

- 列 c ごと: 模型の掘り W_c / nt_c と実際の dig、取っ手 h_c の穴の項 q_c（4 kHoleWeight を掛ける前。印刷の規則の穴と、穴あけの後の穴）と、列 c を掘った fix・fdig・fill の数、穴埋め紙の手の割り当て（その注文で別の列の紙が見せた穴に等分）。
- 目標の列 c と種類（単独 / 対）ごと: 注文あたりの dig・fix・fdig・fill と、外に出ている穴埋め紙を動かした手（fout）、穴の数、穴 1 つあたりの手数、模型の穴の取り分（穴ごとに 4 kHoleWeight q_j / N_j）、持ち上げた目標の紙を列へ戻すまでの手（tret）。
- 目標の穴の数 h ごと: 穴 1 つあたりの手数と、穴が列の先頭で見えた割合（残りは穴埋め紙など）。
- 取っ手 h_j ごと: 注文の前の列の先頭（列の中にある最初の紙）が要求と違う色だった割合と、模型の 2 q_j / N_j、fix の 1 回あたりの手数。

紙の状態（列の中か、持ち上げた目標か、穴埋め紙か）は、ラベルの列から決める（lift で目標、fill・help で穴埋め紙、ret・fret で列に戻る）。取っ手の窓は、汎用紙がどれも穴で、窓 63 でない窓のうち、そこが不透明な列の紙の列の最小値で順に決める。

## by_time.py

`python3 solutions/label-audit/by_time.py RUN [--seeds 0-2000]`

注文の番号（0、1、2〜3、4〜7、…）ごとの、ラベル別の注文あたりの手数。最初の重なりの影響を見る。

## regress.py

`/home/sato/ahc074/.venv/bin/python solutions/label-audit/regress.py RUN`（numpy を使う）

seed ごとの実際の手数（全体とラベルの組ごと）を、設計が stderr に出す model_col・model_hole・model_gc に回帰する。模型が正しければ係数はどれも 1 になる。
