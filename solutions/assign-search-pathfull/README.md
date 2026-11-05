改良元: solutions/esw-clean

保存した良い割り当てへの経路探索と両向き弧による正確な簡易判定を併用する。保存状態との汎用・ハンドルの役割の違いだけでなく、両方で汎用の窓の辺と極性の違いも、既存の反転・辺移動近傍で埋める。目標に1つ近づく候補を、従来の3組損失スクリーンを通るものから選ぶ。受理と全組目的関数は従来のまま。保存状態は8区画。近傍比率・温度・停滞閾値は変えない。

AS_ELITE=1 / AS_SCREEN=1 / AS_WORK=1が既定。前2つは経路探索・簡易判定の有効無効、AS_WORKは時間合わせ用の反復倍率。AS_PROFILE（コンパイル時既定0）と全既存のスイッチ・プロファイラ・ログ・CLOCK_SCALE・LOCAL_BENCH・DesignStore・@paper/@opsを保持する。

elite_*は保存・試行・評価・受理回数、path_starts / path_complete / path_blockedは経路開始・割り当て一致・適格候補なしの回数。path_internalは汎用窓の辺・極性を合わせる候補数。direct_checks / direct_rejectsは簡易判定回数と棄却数。
