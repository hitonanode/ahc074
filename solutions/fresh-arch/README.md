# fresh-arch: 今の解法を知らない agent による、構造のゼロからの検討

改良元: なし（解法ではなく、研究の記録）。

- 今の解法の構造（汎用層・キャップなど）を知らせずに、問題文・テスター・既知の基本技法（専用紙、2 目標の共有紙、列の階段）と既知の最良の手数の内訳だけを渡して、1 注文の手が少ない構造を考えさせた。
- prompt_agent.md: agent に渡した依頼文。prompt_web.md: 同じ依頼を Web の対話 UI に貼るための版（問題文を末尾に含む）。
- REPORT.md: agent の報告と、依頼者による今の設計との照合。
- sim/: agent の模擬（専用紙だけの階段 stair.cpp、共有込み full.cpp、階段でない freeorder.cpp、式 formula.py、組の統計 pairs.py）。
- bias_check.py: as6-cap38p0 の設計で、ハンドルごとの穴の色の偏りと、対の違う窓の穴の数を集計する。
