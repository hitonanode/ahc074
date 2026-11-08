改良元: solutions/dcomp-combo-alt1

2→1/1→1修復の各削除組について、最上位所有窓のmaskを修復候補の順番で保存する。候補以外の紙はこのmask判定で読まれない。候補の判定順、整数mask、可視性と得点評価は同じで、stampとownerの2回のgatherを1回の連続loadに置き換える。

検証用EJECT_OWNER_CHECKでは元の紙番号別maskと全候補を照合する。探索予算は親と同じ、時計による変更はなく、既存ログ・trace・profiler・DesignStoreを保つ。
