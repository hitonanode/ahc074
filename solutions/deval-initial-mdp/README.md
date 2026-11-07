改良元: `solutions/deval-seven-wide`

完成設計をVで選んだ後、注文を知らずに列内の初期の紙の順番を最適化する。既存の列MDPを作り、各列の完全状態で相対価値Fが最小の型列を選ぶ。同じ型の紙はfiller需要を含む重み順に置く。

紙の模様と所属列は保ち、列内の紙番号とdedを対応して更新する。DesignStoreには更新後の設計を保存し、リプレイはそのまま読み込む。最適化は各候補ではなく最終設計に一度だけ。`initial_order_changed` は変わった位置数、`initial_order_model_gain` は模型の差、`initial_order_sec` は追加時間。全探索予算は固定で時間不足による変更はない。
