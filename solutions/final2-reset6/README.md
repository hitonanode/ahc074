改良元: solutions/final-time-pace-fix2

Design::reset_strength を2.0から6.0にする。列への注文で頭色が戻る効果を、設計の穴費用で強く見積もる。fix2の設計時間管理（総予算1.22秒）、注文のペース配分（1.88秒／最終1.92秒）、NOINIT、および2か所の範囲外参照の修正を引き継ぐ。

根拠は固定反復版 d30a-reset6 の2000件比較。GCCの `20261109-114428_dcomp-combo-dual30` / `20261109-114428_d30a-reset6` で −0.0861 ± 0.0217%、Clangの `20261109-113526_dcomp-combo-dual30` / `20261109-113527_d30a-reset6` で −0.1247 ± 0.0220%（±は標準誤差）。covered_gainの返却費用を0.8に増やす変更は、reset6への追加で悪化したため含めない。

LOCAL_BENCH の D30A_RESET でreset係数を指定できる（既定6、親は2）。DESIGN_FIXED_ITERS=1、DESIGN_SECONDS、DesignStore、解析用注釈、その他の既存スイッチとログを保つ。段の目印と目次も親と同じ。新しいstderr指標はない。

設計の時間比率は固定反復200件の測定（20261109-122337 の fix2 / final2、GCC既定とClang提出相当）から再計算した。helper準備が8.9%短縮するなど5段で3%を超えたため、各段の両コンパイラの平均時間を等重みで合算し、合計で正規化した。総設計予算1.22秒とpacerの期限は維持する。詳細は solutions/impla-notes/final2-shares.md。検査と最終的な比率の判断は solutions/impla-notes/REPORT-final2.md に記録する。run.py は親の評価補助、check_submit.py はプリプロセス後のトークン一致と警告差の検査である。提出用submit.cppはmain.cppの先頭インデントを4桁ごとのタブに変換して作る。
