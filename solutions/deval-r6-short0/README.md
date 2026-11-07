改良元: `solutions/deval-flex125-plan3`。

追加計画を手数によるshortlistで除かず、費用順に本探索する。探索件数上限は同じ。 設計は変えない。

呼出しのないsolve_edgesと旧add_filler_featuresを削除し、誤ってVで巡回受理と記載したコメントを修正。ログ・プロファイラ・実験スイッチ・目次は維持。予算は固定、時間不足による切替えなし。
