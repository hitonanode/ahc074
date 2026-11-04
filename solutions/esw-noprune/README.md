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
