# hole-relax

改良元: solutions/gen-relax と solutions/hole-level3（合流）

- 紙の設計（G の窓・ブロック分け・Y_b の山登り、Y_b を固定した後の整合する相方からの組み替え、整合しない対のブロック分割。ブロック 6 窓、H = 34）は gen-relax から取った。
- 注文ごとの操作は、search-bf2 → hole-level → hole-level2 → hole-level3 の差分をそのまま gen-relax に当てた（gen-relax と hole-level3 はどちらも search-bf2 から分かれ、前者は設計側、後者は注文処理側だけを変えている）。段付き穴埋め紙、区間スケジューリングの DP、持ち上げる前の穴埋め紙の選択、前の専用紙・前の穴埋め紙の再利用とその場に残す選択肢、列の外に残す紙の費用 0.8 手、残した紙が見えている計画だけを採ること、焼きなましの打ち切り 1.10 秒、がそれに当たる。各説明は solutions/hole-level/README.md 〜 solutions/hole-level3/README.md。

## 合流の後に変えたところ

- 列から取る穴埋め紙を採る条件を、「掘りを 3 + 深さ 手以上省く」から「2 + 深さ 手以上省く」に緩めた（3 か所の候補の生成すべて: 持ち上げた後の貪欲、持ち上げた後の DP、持ち上げる前の DP）。列の外に残した紙は、次の注文で戻されずに再利用されたりその場に残されたりすることが多く、戻しの 1 手を払わないことが多いため。前の穴埋め紙を新しい段へ移す条件（省ける掘りが 2 手以上）は変えていない。

## パラメータと指標

- 環境変数: gen-relax の設計側のもの（`CB_S` = 6、`HUB_H` = 34、`CB_PSWAPS` = 3000 など）と、hole-level3 の注文側のもの（`FILL_W` = 0.8、`PRELIFT`、`KEEP_HARMLESS` など、`HUB_TL` = 1.10）に加えて、`FILL_COST`（既定 1。穴埋め紙を採るのは、省ける掘りが FILL_COST + 1 + 深さ 手以上のとき。hole-level3 は 2 に当たる）。
- stderr の指標は gen-relax（`block_log_consistency`、`split_fallback`、`split_failed`、`anneal_iters` など）と hole-level3（`prev_fillers_used`、`refill_plans_used`、`pred_out_returns` など）を合わせたもの。
