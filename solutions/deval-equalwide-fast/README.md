改良元: `solutions/deval-equalwide6`。

ejectの必要条件を4紙ずつ整数AVX2で検査し、cache keyを16byte入力・8lane圧縮で作る。通過候補の順、キーの全一致検査、浮動小数点の計算は保つ。呼出しのないfeature exportメソッド2つと古いコメントを削除して容量を確保した。品質に関わる変更は次の改良元と同じである。

NEUTRAL_WIDTHを3から4へ増やす。設計とその他の注文予算は同じ。

単独helperの同generic距離候補を見積り上位1件まで追加し、最少generic距離のgoalは既存futureの低い方を選ぶ。元のgeneric移動を減らすhelperは残し、合計上位6候補とする。時計による切替えはない。元のログ・注釈・実験スイッチを保つ。


基準の固定予算、ログ・統計・注釈・実験switch・profiler・段の目印を保つ。時刻による切替えはない。
