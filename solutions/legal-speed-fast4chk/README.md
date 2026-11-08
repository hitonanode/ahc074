# legal-speed-fast4chk（legal-speed-fast4 の飛ばす条件を確かめる版）

改良元: `solutions/legal-speed-fast4`。何も飛ばさない（出力は legal-speed-fast と同じ）。提出用ではない。

- fast4 が飛ばす直しの候補（`eject_skipped`）も evaluate にかけ、その列が見えない手なしで再生できた回数か採用された回数を `eject_skip_mismatch`（0 なら正しい）に、調べた試行の数を `eject_skip_checked` に出す。
