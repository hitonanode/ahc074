改良元: solutions/argon-des-perf-rematch-v2

穿孔後Hungarian再割当の既定回数を1回、フィラー係数を0.70にする。
初期の設計・穿孔は同じで、穿孔後の追加穴を物理的な紙の位置に固定する。
ARGON_D2_LATE_ITERSは回数の上書き用。比較では環境変数を設定しない。
d2_rematch_*、d2_model_initial/final、d2_filler_initial/final、d2_extra_remainingで
変更量・予測差・時間を測る。全ログ・プロファイラ・既存スイッチ・DesignStoreを保持する。
