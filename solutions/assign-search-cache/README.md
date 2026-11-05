改良元: solutions/esw-clean

全組の評価を行う候補・順序を変えず、閉包計算前に関係の正確な費用を再利用する。向きをすべて逆転した関係は2目標分の費用が同一なので、小さい30bitキーに正準化する。完全なキーと費用を64bitの1要素に詰め、16384要素（128KiB）の表に保存する。衝突はキーを照合してmissにする。missには従来のAVX2閉包とPosetSumsを使用する。過去に撤去された2MiBの関係キャッシュとは、正準化と単一ロード・小さい表が違う。

AS_CACHE=1（既定）は有効、0は無効。AS_WORK=1（既定）は窓割り当ての反復倍率。as_cache / as_workは使用設定、relation_cache_hits / relation_cache_missesはヒット・ミス数。既存の全ログ・設定・プロファイラ・CLOCK_SCALE・LOCAL_BENCH・DesignStore・@paper/@opsを保持する。整数の費用をそのまま使い、乱数・候補順・判断に関わる浮動小数点演算を変えない。
