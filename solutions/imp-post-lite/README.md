# imp-post-lite

改良元: solutions/imp-post

後処理（post_optimize）のうち、2 つの編集の同時削除と eject（2 つ消して 1 手で直す）を外した軽量版（先頭に `#define POST_PAIRS 0` を足しただけ）。残るのは 1 つの編集の削除とアンカーの付け替え。重い近傍の効果と時間の釣り合いを見るため。
