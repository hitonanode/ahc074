改良元: solutions/dcomp-combo-alt1

anchor候補を固定配列にする。さらに各anchor走査で途中の勝者を毎回anchorizeせず、最後に採られたbest_opsだけをanchorizeする。走査中のeditsは元から固定されており、試す候補と選択は変わらない。

固定探索予算、既存ログ・実験スイッチ・profiler・目次と段、DesignStoreは保持。時計による分岐は追加しない。
