改良元: solutions/d30a-reset6

設計モデル定数のscreenで選んだ変更を重ねる。

- headreset=6.0: climb/ProbabilityHead の先頭色確率だけの reset 需要倍率。焼きなましの reset_strength=6 は維持し、確率側に残った2との不整合を検査する。 環境変数: D30B_KHEADRESET（既定 6.0、基準値 2.0）

固定反復回数、CLOCK_SCALE、DesignStore、既存ログを維持する。reset_strength、covered_gainの返却費用、fret-full、V回帰係数は変更しない。追加stderr指標なし。
