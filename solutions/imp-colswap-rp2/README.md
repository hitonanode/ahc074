# imp-colswap-rp2

改良元: solutions/imp-colswap-rp

焼きなましを速くしただけで、手・割合・乱数の引き方は imp-colswap-rp と同じ（回数を固定すると出力が一致する。seed 24〜26 で確認）。

- 対と単独の単位の一覧（対の組み替えで使う）を、焼きなましの本体のループの局所変数から Annealer のメンバに移した。局所変数のままだと、組み替えを使わない設定でもループ全体が約 7% 遅くなっていた（-DSIM_HARNESS のビルドで、回数固定・1 コアに固定した CPU 時間の計測。cmp-anneal 0.52 秒 → 0.57 秒、メンバにして 0.52 秒）。
- 対の組み替えの相手選びをループから関数 pair_replace（インライン化しない）に出した。
- 焼きなまし 600 万回の CPU 時間（同じ計測、-DSIM_HARNESS のビルド）は cmp-anneal 比で、imp-colswap-rp の約 +9% から約 +6% になった。ただし提出と同じビルド（-DSIM_HARNESS なし）の時間制の評価では、焼きなましの回数は imp-colswap-rp と変わらなかった（速くなったのは模擬のビルドだけ）。

`-DANNEAL_CHECK` の照合は H = 28, 32, 36 で通る。パラメータと stderr は imp-colswap-rp（と imp-colswap の README）と同じ。
