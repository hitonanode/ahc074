改良元: solutions/argon-req-completefast-v3

穿孔の色標本を16個の層別標本にする。
目標・列ごとに一様分布を16等分して1標本ずつ抽出し、列ごとに独立に並べ替える。
32標本で得た改善を、より少ない計算量で維持できるかを検証する。
受理係数0.7、owner条件付け、利益上限、差分キャッシュは基準と同じ。値だけの連続配列は加えない。

追加の環境変数・指標はない。全ログ・@paper/@ops・プロファイラ・予算スイッチ、CLOCK_SCALE、
LOCAL_BENCH、DesignStore、段の目印と目次を保持する。変更はHandle perforationだけ。
