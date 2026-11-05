改良元: solutions/argon-des-perf-latew105

穿孔後再割当の後に、現在のheadで穴の追加・復元を1巡行う。
元のペア穴・自列ハンドル・汎用窓・capは保つ。係数0.7、32層化標本。
再割当前後で所有紙の穴、headの有効区間、関係する標本の色が全て同じなら、
以前の区間DP表を再利用する。区間ごとの最大値・加算の順序は変えない。
同じ固定seedで作る層化一様乱数も再利用する。

ARGON_D2_ALT_PASSESの既定値は1（0で追加段なし）。ARGON_D2_WARM_VERIFYを定義すると、
再利用したDP表を全て独立に再計算し、forward/backward/avoid/valueを完全一致で照合する。
d2_alt_reused_rows/verified_rowsは再利用数/照合数（各段8192標本）。
d2_alt_build_sec/search_sec/sec/end_secは準備/探索/段全体/終了時刻。
d2_alt_trials/accepts、before/after/added/restored、cost/owner/donorは
候補/採用数、穴数、穴費用/所有目標の条件付き価値/他目標への価値の差（手/注文）。
既存ログ・スイッチ・プロファイラ・DesignStoreを全て保持。
追加段と目次項目はdesign_papers: alternating perforation and reassignment。
