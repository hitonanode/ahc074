改良元: `solutions/deval-trim6b`。

列MDPを次状態のplan_costへ加える既定重みNEXTMIXだけを0.5から0.25へ下げる。挿入位置のMDP重み、one-step模型、設計と探索予算は変えない。列ごとのMDPが互いのfillerを独立に扱うことによる、次状態価値の過大計上を弱める実験。全ログとスイッチを保ち、時刻では切り替えない。
