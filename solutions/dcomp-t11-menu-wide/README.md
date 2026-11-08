改良元: solutions/dcomp-combo-alt1

残る既知の予算拡張をまとめて測る研究用: REPEAT_MIN0、RWF、ALT1.5、width12、slack0（正の費用余裕なし）、通常候補8、expanded候補8。追加computeの到達点を確かめるもので、時間条件を満たす提出候補とは扱わない。

固定回数を両コンパイラで共用。設計・既存ログ・trace・profiler・実験スイッチ・段・DesignStoreは保持。時計による予算変更なし。予算拡大の研究版は通常評価なら--no-recordを使用する。

注意: NEUTRAL_SLACK=0は無制限ではなく、通常候補に正の費用余裕を与えない。promising候補には既存の.75が残る。この測定を追加探索の上限とは解釈しない。
