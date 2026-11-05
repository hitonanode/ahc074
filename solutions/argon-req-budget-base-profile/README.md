改良元: solutions/argon-des-perf-latew105

R5の時間・利得測定。COLFAST_PROFILE/F3_PROFILEとPLAN_TRACE/HEAVY_PREDICTの既定値を有効化した測定専用版。探索・評価は元と同じ。既存のcfprof_*、#f3post、#f3op、#f2plan、#heavycandで段と候補の時間・利得を測る。全ログ・スイッチ・CLOCK_SCALE・LOCAL_BENCH・DesignStore・目次・節を維持する。固定設計で使用し、時間超過する通常測定では--no-recordとする。
