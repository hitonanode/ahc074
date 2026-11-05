改良元: solutions/argon-des-perf-latew105

D3の全列被覆候補。ColumnMdpの全状態上限40000→250000、部分列上限250000→800000。
長さ上限14、価値反復8回、価値の混合係数は保持する。
基準の2000設計では最大列長12、未被覆の214列は全て状態数の制限によるため、
この上限で全列を厳密な型列MDPに入れられる。
COLMDP_MAXFULL/COLMDP_MAXSUBなど既存スイッチ・指標・ログ・プロファイラ・DesignStoreを保持。
colmdp_columns、colmdp_full_states、colmdp_sequences、colmdp_secで被覆と費用を確認する。
