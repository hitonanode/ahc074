# 2 操作の同時削除（post-prune）を外した版（esw-noprune）

改良元: solutions/esw-tidy

PR 91 のアブレーション（trial_log.md「PR 90 の改良のアブレーション」）で効いていなかった部品のうち、外しても悪くならなかった post-prune だけをコードごと消した版。それ以外（紙の設計・時間配分・注文処理・乱数・CLOCK_SCALE・LOCAL_BENCH）は改良元と同じ。

## 外したもの

- **2 操作の同時削除（post-prune）。** 後処理の編集の段（`// ==== Post-processing: deletions and new anchors of the edits ====` の post_optimize）で、1 操作ずつの削除の後に行っていた、前の注文で持ち上げた紙か穴埋め紙を動かす操作を含む 2 操作をまとめて消す試行。1 操作ずつの削除・差し込み先の変更・削除と差し込み先変更の同時試行・2 削除 + 1 修復は残す。stderr の post_pair_trials・post_pair_accepts はなくなった。

## 外さなかったもの

- 穴埋めの山登り（head-design の filler_climb）: 山登りをなくした solutions/esw-lean は有意に悪かった。as6-canon の山登りに替えた solutions/esw-lean-climb は差がなかったが、コードが長くなる。
- stay-cover・post-repair・post-two・perforated-eight: 軽い計画を使わなかった seed では、測り直し 3 回とも効いていた。
- 穴費用の係数 kHoleWeight = 0.38（0.40 に戻しても差はないが、コードの量は変わらない）。

いずれも結果と戻し方は trial_log.md にある。

## 設計の保存と読み込み（LOCAL_BENCH、scripts/pahcer_run.py の --save-design / --design-from）

注文処理だけの変更を、同じ設計の上で比べるための仕組み。`-DLOCAL_BENCH` のときだけ働き、提出版の動作は変えない。

- 設計の結果（注文処理に要る状態）を `DesignState` にまとめた: 汎用紙の数 M・汎用窓の数 G・取っ手の数 H、窓の並べ替え、並べ替えた後の目標、比較器の対と色、穴あけの後の 192 枚の紙、各紙の列、各目標の紙、取っ手の窓。
- main の設計の段（窓の割り当て〜穴あけ）を関数 `design_papers` に移し、Solver の準備を `make_solver`（DesignState から Solver を作る）にした。main は「設計（または読み込み）→ make_solver → 補助紙の表と先読み → 紙の出力 → 注文」の順になる。穴あけは design_papers の中で、印刷したままの紙から作った Solver の上で行い、その結果の紙を DesignState に戻す（main は穴あけの後の紙から Solver を作り直す。元の Solver と同じ中身になる）。計算と時計を読む回数は改良元と同じ。
- 環境変数 `DESIGN_SAVE_DIR` があると、設計の終わり（補助紙の表と先読みを作った後、紙を出力する直前）に、DesignState と、補助紙の表を作り終えたか、design_papers の stderr、プログラム開始からの経過時間を `<dir>/<hash>.txt` に書く（hash は入力のバーコードの FNV-1a。注文の列だけが違う入力は同じファイルを使う）。
- 環境変数 `DESIGN_LOAD_DIR` があると、設計をせずにそのファイルを読む（ないか、入力と合わなければ `design_store_error` を出して終了コード 1 で終わる）。保存した stderr と `design_loaded = 1` を出し、Solver・補助紙の表（保存した run で作り終えていなければすぐにあきらめる）・先読みを作り直す。設計の終わりで、時計がそこから保存した経過時間の続きを読むように開始時刻をずらす。そのため、注文処理の stderr（req_sec、end_sec、helper_end_sec など）も元の run の時間の続きになる。
- 注文処理のコードが同じなら、読み込んだ run は保存した run と同じ紙と操作を出す。注文処理を変えた解法でも、DesignState の形が同じならその設計を読み込める。

esw-tidy と esw-noprune の両方に同じ変更を入れた。確認（それぞれの改良前の版と比べて。時計を、読むたびに一定時間進む擬似時計に置き換えた版で）: seed 0〜39（1 回 20 µs）、40〜55（200 µs。設計の各段が早く打ち切られ、補助紙の表をあきらめる）、56〜60（2 ms。緊急設計）の 61 件で、(1) LOCAL_BENCH なしで改良元と stdout・時計を読む回数が一致、(2) LOCAL_BENCH で改良元と一致、(3) 保存した run と読み込んだ run の stdout が一致し、stderr も `design_loaded` の行と、補助紙の表をあきらめたときの helper_papers（読み込んだ側は途中までの数が違う）を除いて一致（end_sec などの時刻も一致）、(4) 同じバーコードで注文の列だけを変えた入力でも、保存したファイルが同じで、元の入力の設計を読み込んだ run が、その入力で保存した run と同じ stdout、(5) LOCAL_BENCH で軽い計画を止めないようにした版（時刻で手が変わる）でも保存と読み込みの stdout が一致（esw-tidy で、読み込みで時計をずらさない版では 6 件中 6 件が不一致）。実時計でも（esw-tidy）、gcc と clang の版で保存と読み込みの stdout が一致した（4 件ずつ）。
