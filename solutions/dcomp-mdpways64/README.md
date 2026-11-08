改良元: solutions/dcomp-screen-replay

列MDPの正確なtype列cacheを列ごと16から64項目へ拡大して衝突を減らす。keyは衝突のない長さ付き2bit列、値は元のfloatをそのまま保持。計算式、浮動小数点、固定予算、ログ、実験スイッチ、DesignStoreは不変。時間fallbackなし。
