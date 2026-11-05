改良元: solutions/esw-slim

D2の追加穿孔。基準のhead穿孔を保ち、非head第2候補の露出率を0.125とする。
非headが現れるかを8標本から抽選する処理をやめ、各列の区間辺で両色の紙の組合せを全列挙して期待値を計算する。
色は従来の8標本。紙の同定の抽選誤差を除き、低頻度の候補の利益を過大評価しないための比較。
区間DPは期待辺利益を最大化する（期待される最大利益の厳密値とは異なる）。

ARGON_D2_RATE、ARGON_D2_WIDTHとd2_*指標はargon-des-perforationと同じ。
既存ログ・プロファイラ・CLOCK_SCALE・LOCAL_BENCH・DesignStore・段の目印を維持する。
共通報告はsolutions/argon-des-perforation/REPORT.md。
