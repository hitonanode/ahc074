改良元: solutions/esw-clean

良かった割り当てへの連続した経路探索（assign-search-path）と、両向きの弧による正確な事前判定（assign-search-screen）を併用する。保存状態は8区画、既存の温度・通常の近傍比率・3組損失閾値・停滞閾値は変更しない。目標の汎用窓集合に近づく交換を、受理される間続ける。集合に到着したら別の保存状態を選び、候補がなくなるか拒否されたら通常の探索に戻る。

AS_ELITE=1 / AS_SCREEN=1 / AS_WORK=1が既定。前2つは経路探索・簡易判定の有効無効、AS_WORKは時間合わせ用の反復倍率。AS_PROFILE（コンパイル時既定0）、全既存スイッチ・プロファイラ・ログ・CLOCK_SCALE・LOCAL_BENCH・DesignStore・@paper/@opsを保持する。

elite_*は保存更新・試行・評価・受理回数、path_starts / path_complete / path_blockedは経路開始・集合への到着・適格候補なしの終了回数。direct_checks / direct_rejectsは簡易判定回数とそこでの棄却数。詳しい検証はsolutions/assign-search/REPORT.md。
