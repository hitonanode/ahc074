改良元: `solutions/deval-helper-wide`。

単独helperの事前順位で、覆わないhandleのfix費用だけに1.5を掛ける。実際の残りhandleはfillerでも修正するので、fixのみの見積りを弱める（または対照として強める）。候補実行後のplan_costと選択は変えない。設計・候補数・注文予算・ログ・trace・profilerは同じ。時刻による切替えはない。
