# imp-relax

改良元: solutions/imp-fast

後処理（post_optimize）で、汎用紙 6 枚が連続していることを求めないようにした（solutions/gpt6pro-07-02-replace の BARCODE_RELAX_GENERIC）。

- 汎用紙の間に残った列の紙は、canonicalize でレベル 0 の穴埋め紙として記録され、穴埋め紙に手が届く（fillers_reachable）ことは引き続き確かめる。次の注文では、その紙を残したまま汎用紙を並べ替える計画は set_generic で無効になり、列に戻す計画が使われる（補助紙のときと同じ）。軽量処理と最後の手段の計画は、最初に穴埋め紙をすべて戻す。
- 補助紙の計画（汎用紙が分かれている）にも後処理をかける（imp-fast は飛ばしていた）。
