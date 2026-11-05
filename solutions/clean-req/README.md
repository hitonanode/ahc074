改良元: solutions/time-alloc

注文処理を整理した版。設計・共通部・ヘッダ目次・領域間のインターフェースは変更しない。

- 前の商品紙をその場に残す `ret_mode=4` の候補と専用処理を削除する。フィラーが次の注文でも役立つことを評価する `stay_table` は別の機能で、維持する。
- 前回の同一クエリの計画・補助紙配置を記憶する機能を削除する。`QM_MODE` は廃止する。`qm_requests` は注文数、ほかの `qm_*` 指標は互換性のため0を出す。
- アンカー化、計画初期化、紙とリンクの移動、ejectの反復、補助紙配置の重複を共通化する。可視性・失敗時の処理・操作ラベルの順序を保つ。
- 既定で無効だったF3_CANON・F3_SHARED_VIS・F3_CROSS_MEMOの実験経路を削除する。対応するf2_canon_*・f2_visibility_*のログ名は0として残す。通常のF3_MEMO・F3_PREFIX等の有効なキャッシュは維持する。
- SearchConfigは型・環境変数名・既定値を同じ宣言にまとめる。後処理の初期積層の二重保存をなくし、操作列の共通型をMovesとする。冗長な導入コメントとインデントを整理する。

eject・中立候補の再編集・フィラーチェーン・フィラーの同時選択は、ablationで寄与があるため維持する。通常3本の候補と重複する追加計画の経路も、F3_MODE=2等の大きい予算で使うため維持する。

全てのstderr指標名、@paper/@ops、heavy traces、COLFAST_PROFILE・F3_PROFILE等のプロファイラ、CLOCK_SCALE、LOCAL_BENCH、DesignStore、非常用設計を維持する。F3_*の探索予算とCOLMDP_*、設計の予算スイッチは継承する。
主な指標は `req_sec`（注文計画時間）、`*_end_sec`（各設計段の終了）、`end_sec`（全体終了）、`total_moves`、`self_wrong`、`op_label_errors`。削除した機能の指標も消さない。

全ablation・出力一致・最終比較・行数はREPORT.md。比較はscripts/pahcer_run.pyのみで行い、通常runを記録する。
