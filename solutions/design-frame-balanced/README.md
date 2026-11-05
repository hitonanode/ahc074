改良元: solutions/esw-clean

design-frame-ordercost と同じ、ハンドル順の価値を加えた割当目的関数を使う。
追加の評価費用を賄うため、窓割当の反復回数を基準の82%（369,000回 + climb 109,060回）にする。
その他の段の回数は基準と同じ。FRAME_ORDER_WEIGHT（既定0.5）、MAP_ITERS / GOPT_STEPS を使用できる。
その他のログ・設定・プロファイラ・DesignStore・紙属性・操作ラベルを維持する。
