改良元: solutions/argon-des-perf-gaincache

穿孔後に同じ確率・標本・headを使い、
同じ候補順でもう1周、係数0.7で穿孔・復元を試す。
再構築する案の対照として、単に2周目を足す効果を分離する。
追加段の受理数・穴数差・色確率の絶対差和・時間をd2_accepts/holes_delta/probability_shift/secに出す。
新しい環境変数はない。全既存ログ・@paper/@ops・プロファイラ・予算スイッチ、CLOCK_SCALE、
LOCAL_BENCH、DesignStore、段の目印と目次を保持する。
