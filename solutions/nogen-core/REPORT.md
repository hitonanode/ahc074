# 未使用設計経路の削除

main.cpp: 485285 bytes（所有者距離高速化版504311 bytesから19026 bytes減）。

mainの設計呼出しはdefault引数のdesign_papers(originalA)だけで、先頭からdesign_controlsへ返る。削除したforcedG本体は、その到達しない本体自身からのみ再帰的に参照されていた。EconomicDesignとanchor_rebuildもその本体だけから使用。緊急設計は呼出しなし。既定の全ログ、監査、プロファイラ、保存機能と段マーカーを保った。

assertの行番号が変わるため通常オブジェクトの同一性だけでは判定できない。通常500ケースの完全出力一致を確認する。

通常比較 `20261106-161243_nogen-initial-value` と `20261106-161243_nogen-core-initial` の500件で、この削除を初期積層変更版へ適用する前後のstdoutが全件完全一致した。core単体を別に評価したとは主張しない。g++/clang++、bench有無の4通りで-O2 -Wall -Wextra -Werrorの実ビルドを通過した。
