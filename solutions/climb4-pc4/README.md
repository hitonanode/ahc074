# esw-climb4 + 後処理する計画 4 本（climb4-pc4、計測用）

改良元: solutions/esw-climb4

PR 115 の「後処理の候補を 4 系統へ」（solutions/postcand で esw-fixiter 比 −0.040%）が、fast2 の計画の選別と列 MDP の入った今の最良版の上でも効くかを測る。差分は `Solver::kPostCandidates` を 2 → 4 にしただけ。
