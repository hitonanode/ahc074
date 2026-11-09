改良元: solutions/d30a-reset6

設計モデル定数のscreenで選んだ変更を重ねる。

- perfreset=6.0: 穿孔の色確率と追加穴費用に残った reset 需要倍率。両方を同時に変え、焼きなましの reset_strength=6 は維持する。 環境変数: D30B_KPERFRESET（既定 6.0、基準値 2.0）

固定反復回数、CLOCK_SCALE、DesignStore、既存ログを維持する。reset_strength、covered_gainの返却費用、fret-full、V回帰係数は変更しない。追加stderr指標なし。
