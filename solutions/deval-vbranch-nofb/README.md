# deval-vbranch-nofb

改良元: `solutions/deval-vbranch-o3`。

ユーザーの指示（2026-11-07）で、時間不足のときの軽い処理（fallback）を外した版。fallback は最終日に入れる（PR #117 以来の方針）。どの注文も常に全部の探索を行い、設計もいつも 4 候補を最後まで作る。時間がかかれば、そのまま end_sec と実時間（ジャッジでは TLE）に出る。

外したもの（どれも deval-vbranch-o3 に残っていて、最終日に戻せる）:

- **注文処理の軽い処理（提出時だけ）:** 残りの注文の割合を q として、1.84 − 0.12q 秒から中立探索を省く処理と、1.90 − 0.30q 秒から最初の合法な計画を使う処理。統計の `light_requests` / `hard_light_requests` も外した。
- **設計の段の打ち切り（提出時だけ）:** 窓の探索 0.85 秒、窓の climb 0.90 秒、焼きなまし 1.15 秒、filler climb 1.25 秒。
- **候補の打ち切り:** 設計の経過が 1.12 秒を過ぎたら次の候補を始めない処理（`DEVAL_DESIGN_LIMIT`）。手元の評価でも働いていたが、2000 件中 2 件で候補が 3 個になっただけだった。

手元の評価（LOCAL_BENCH）では、上の 2 つはもともと止まっていた。そのため、出力は deval-vbranch-o3 と同じで、違うのは 3 つ目が働いていたケースだけ。

設計の作り方、V、パラメータ、stderr の指標は deval-vbranch-o3 と同じ（`../deval-vbranch-o3/README.md`、`../deval-vbranch-o3/REPORT.md`）。V の係数の参照用 JSON は `../deval-vbranch-o3/V.json`。
