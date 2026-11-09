# ia-nextkey

改良元: `solutions/dcomp-combo-dual30`。

`adaptive_next_cost` の完全一致キャッシュで、キーのうち汎用層より下の filler 記録 `(紙ID,水準)` だけを正規化する。`IA_NEXTKEY_MODE=1`（既定）は紙ID・水準順に整列し、`=2` はさらに、同じ不透明窓を見せる水準を最初の不透明窓の番号へそろえる。`=0` は親のキー。実際のfiller記録と、列内の紙の順序は変えない。

正確性の根拠: 費用関数がfillerを使う箇所は、除外紙と利用可能色の真偽設定、およびstay_tableの被覆率の要素ごとの最大値。これらはfillerを列挙する順番に依存しない。stay_tableは `h_opq[paper] & ~low_bits(level)` だけで決まるので、同じmaskになる水準も同じ値になる。列内の紙を加算する順序は元のままであり、浮動小数点の演算を組み替えない。

`IA_NEXTKEY_CHECK` は、cache hit時にもキーを正規化しない元の関数を計算し直し、doubleの全bitが一致することを確かめる。missも既存NEXT_PREFIX_CHECKで照合する。確認ビルドの時間は高速化の判断に使わない。

指標 `ia_nextkey_reordered` は挿入ソートで位置が変わったfillerの数、`ia_nextkey_level_changed` はキーだけの水準を変えた数。`cf_value_hits/misses` は親と同じ。設計、候補、選択、操作ラベル、時計の倍率は維持する。
