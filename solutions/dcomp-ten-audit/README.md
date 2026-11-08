改良元: solutions/dcomp-ten-fast

候補の同一性を検査する診断版。各完成候補についてVとcurのdoubleのbit表現、乱数状態、DesignStateの全ての設計値、raw unit割当を@dcomp_candidate行へLOCAL_BENCHで出す。選択や乱数は変更しない。元の固定予算・注文処理・ログ・実験スイッチを保持し、時間不足の切替は加えない。
