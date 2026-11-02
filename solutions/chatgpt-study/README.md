# ChatGPT による構造変更の研究

改良元: `solutions/imp-combo`。このディレクトリは提出用解法ではなく、今回追加した実装と検証の入口。

詳しい結論、比較条件、ケースごとの成績は [REPORT.md](REPORT.md) を参照。

| ディレクトリ | 役割 |
|---|---|
| `../chatgpt-fixed-columns` | 同じ新方策を1列単位で使う対照実装 |
| `../chatgpt-free-triples` | 隣接3列の紙順を自由にし、合法な同時穴修正を探索 |
| `../chatgpt-free-context` | ブロックが使われる確率で将来費用の尺度を補正 |
| `../chatgpt-free-fill` | 自由順序にブロックをまたぐフィラーと据え置きを追加 |
| `../chatgpt-free-lex` | 最少手数、その同点内で将来費用を比較 |
| `../chatgpt-free-joint` | 同点評価を複数窓の同時修正距離に置換 |
| `../chatgpt-local-macro` | imp-combo の既存機能を保ち、最後の3列修正を再探索 |
| `../chatgpt-block-mdp` | 6枚・720状態の厳密な合法グラフと平均費用MDPの研究 |
| `../chatgpt-permutation-code` | 複数の商品を紙の順列で表す符号の実現可能性の研究 |
| `../chatgpt-eval` | 対話テスターのC++移植、入力生成、独立再生、固定終状態の下界解析 |

提出可能な各試作の `main.cpp` は単一ファイルで完結する。各解法のREADMEはアルゴリズムとパラメータを説明し、結果はこのレポートおよび `trial_log.md` に分けて記録する。

`collect_results.py` は、PIPEで捕捉して検証済みの評価記録からケース別CSVと比較統計を作る。異なる入力集合は比較せず、入力・紙設計・ソース・出力のhashを併記する。`evidence/` には採点を再生できる出力と入力を圧縮して保存する。従来形式の出力から事後検証した下界解析用の8記録は、PIPE方式の評価と区別する。
