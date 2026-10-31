# tail-probe（分析用のスクリプト。提出用の解法ではない）

改良元: なし（solutions/brk-probe の `REQ_PROBE=1` の出力を読む分析スクリプトだけ）

1 注文の手数の裾（手数の多い注文・目標）を調べるためのスクリプト。入力は brk-probe を
`REQ_PROBE=1 HUB_ANNEAL=12000000 CLIMB_ITERS=60000` で走らせた stderr のディレクトリ
（solutions/brk-probe/runm.py が `<出力>.err/` に書く）。行の形式は solutions/brk-probe/breakdown.py の冒頭。

- tail.py: 手数の分布、上位 5%・手数 20 以上・手数 6 以下の注文の特徴（対か単独か、列 l、列の大きさ n、D の深さ、
  ハンドルの穴、開始時の不一致、掘った数、触れたブロック、役割別の手数）。同じケースの同じ目標の注文の平均の
  ばらつきを、目標の間の分散と注文の雑音に分ける。モデルの特徴（穴、掘り (n−1)/2、汎用層の実測）を引いた残差の
  目標間の分散も出す。
- holecost.py: 穴 1 個の手数を、ハンドルの深さ m ごと（三角形の穴 m > l と対の穴 m < l を分けて）と、目標の列ごとに回帰する
  （numpy が要る: `uv run --no-project --with numpy python3 holecost.py <dir>`）。
- fitpair.py: 穴に関わる手数（直し・穴埋め紙・古い穴埋め紙の戻し・置き直し・前の専用紙の戻し）を、
  三角形の穴・対の穴の数と対かどうかで回帰する（numpy が要る）。
- bycol.py: 目標の列ごと・対/単独ごとの役割別の手数。
