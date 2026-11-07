改良元: `solutions/deval-trim6b`。

後処理のdisplay検査で、現在の基準操作列の各prefixのlinked-list状態と区間境界を保存する。候補と同じprefixを再利用し、異なるsuffixを通常通り適用する。途中可視性の検査と末端費用・全キー照合は従来通り。

候補の列挙・受理と浮動小数点計算は変えない。親とのstdoutをGCC/Clangで照合し、時間は24並列compareで測る。ログ・実験スイッチ・プロファイラを保つ。
