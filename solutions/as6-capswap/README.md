# as6-capswap: キャップとハンドルの交換と、列の交換による修復

改良元: solutions/as6-cap38（Astra の solutions/astra-cap2/cand2/main.cpp を写したもの。調査の全体は solutions/astra-cap2/REPORT.md）

- キャップを出力上の紙 0 にして、最初から一番上に置く（as6-cap38p0 と同じ。初期設置の 1 手が要らない）。
- 設計の焼きなましの区間の間で、キャップと各ハンドルの交換を試す。新しいハンドルで色が違う対は、別の列の紙と交換して直す（各列に白黒両方、比較器の整合を守る）。列・穴・汎用層の模型の費用が下がれば採用する。
- 割り当て中のキャップ交換や商品の組み替えはしない（as6-capjoint より小さい変更）。時間の区切りは as6-cap38 と同じ。

stderr の指標: `cap_accepted`（交換の採用数）、`cap_swapped_units`（修復で採用した紙の交換数）、`cap_model_gain`（模型の改善量 / 256）。
