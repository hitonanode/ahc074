# imp-910

改良元: solutions/imp10-all

solutions/imp10-all（imp-lean + gpt6pro-10 の工夫: 設計の列の費用、穴埋め紙の隠し合いの許容、最大 4 枚の穴埋め紙の組の探索）に、solutions/imp9-tq の imp-lean からの差分（gpt6pro-09 の工夫: 窓の割り当ての評価を「重ならない 70 対を貪欲に選んだ費用」にし、焼きなましの温度を 0.05 → 0.00125 に合わせ直した。対の汎用層の費用を両方向の和にした）をそのまま当てた。2 つの差分は設計の別の部分（imp9 は窓の割り当てと main の gcost、imp10 は Design の列の費用と注文処理）を変えるので、重なりはない（コメント 1 箇所だけ両方の記述をまとめた）。

中身・パラメータ・stderr は imp9-assign / imp9-sym / imp9-both / imp9-tq と imp10-col / imp10-hidden / imp10-chain / imp10-all の README を参照。
