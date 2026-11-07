改良元: `solutions/deval-shortplus5`。

PLAN_SHORTLIST=6を追加し、1手長い候補の追加後処理を、raw plan_cost が現在の計画の値より1以下の差にある場合だけに限定する。従来のモードとログ、固定予算を保つ。設計はflex125-plan3と同じ。
