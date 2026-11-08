改良元: solutions/dcomp-donor4

rematchのtarget評価でも修復可能集合だけを4 headずつAVX2で計算する。headの整数マスクを元のactive_heads順に連続配置し、gatherを省く。確率多項式、重み、sumの順は元のまま。head更新と同時にblockを再構築する。予算・乱数・ログ・実験スイッチ・DesignStoreを維持、時間fallbackなし。
