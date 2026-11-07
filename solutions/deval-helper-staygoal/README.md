改良元: `solutions/deval-helpeq1`。

同じgeneric移動数のhelper goalを選ぶとき、既存のgeneric terminal value (`0.5*future`) に、helperがgeneric最下段より下へ入る場合の既存filler_charge差 (`kStayStrength*(0.3-stay probability)`) を加える。近い距離を優先する条件は同じ。係数や模型項を新しく学習せず、実際のplan_costが使う項を同手数のgoal選択へ反映する。同距離helperは上位1件、他の候補数・設計・時計に依存しない予算・ログを保つ。
