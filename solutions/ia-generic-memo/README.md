# ia-generic-memo

改良元: `solutions/dcomp-combo-dual30`。

通常の汎用層の並べ替えを1件だけ完全一致で保存する。キーは商品ID・穴mask・汎用紙の並び（紙IDを4bitずつ詰めた値）。ヒットすると、局所vectorの生成、順列番号の検索、到達先の選択、最短操作列の復元を省く。記録した操作列をコピーせず参照するが、各移動は元のmove関数を通り、その時の深さ・可視性・ラベルを維持する。

対象はfuture/satが用意された通常の穴集合だけで、例外の穴集合やM>16では元の計算を行う。MはSolver内で不変で、比較器はM<=12を要するため4bit符号は完全。最初のargminとfutureの同点規則は変えない。先読み表を作り直す時はcacheを失効する。大きな256×720表の前計算は行わない。

`IA_GENERIC_CHECK` でcache hit時にも親の計算を実行し、操作列の完全一致を照合する。`generic_memo_hits/misses` はこの通常経路の再利用/計算回数。設計・要求探索量・時計・既存ラベルは保つ。

既往: gpt6pro-09-01-legal-distにも旧Comparator::planを保存する1entry cacheがあったが、本流imp-fastへ移ったのは全体tail cache。現在のfuture/satによる到達先選択へは入っていない。別系列nogen-control-cacheも類似の背景制御cacheを持つ。この試作は現行の通常経路の重複量を安く測り、単独の出力同一性とClang/GCCの対応時間を確かめるためのもの。
