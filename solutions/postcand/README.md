# 後処理する計画の数（postcand、計測用）

改良元: solutions/esw-fixiter

PR 115 の「後処理の候補を 2 系統から 4 系統へ」を試す計測用の版。注文ごとに後処理（編集パス）をかける計画の数 kPostCandidates（esw-fixiter は 2）を、環境変数 `POST_CAND` で変えられるようにしただけ（未設定なら 2 で esw-fixiter と同じ出力）。計画どうしの重複の扱い（同じ終わりの順序・同じ動かす紙の列はまとめる）は元のまま。
