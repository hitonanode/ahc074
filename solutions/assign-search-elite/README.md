改良元: solutions/esw-clean

停滞時に良かった割り当てへのpath relinkingを1手だけ提案する。状態のハッシュで8区画に分け、各区画の最良状態を保存する。現在とは汎用窓集合の違う保存状態を選び、汎用からハンドルへ移す窓と、保存状態の辺・極性で汎用へ入れる窓を選ぶ。従来の3組損失による事前除外を通る未評価の交換だけを全組評価する。独立した再始動、温度や通常近傍の比率の変更は行わない。

AS_ELITE=1（既定）は有効、0は無効。AS_WORK=0.97（既定）は窓割り当ての反復倍率。AS_PROFILE（コンパイル時、既定0）は1で演算子別の時間・改善量を計測する。
elite_updates / elite_attempts / elite_candidates / elite_acceptsは保存状態更新数、停滞時の試行数、全評価候補数、受理数。既存の全ログ・設定・プロファイラ・CLOCK_SCALE・LOCAL_BENCH・DesignStore・@paper/@opsを保持する。
