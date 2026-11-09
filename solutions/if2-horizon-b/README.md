# if2-horizon-b

改良元: solutions/if2-horizon（HORIZON_F1 = 0.5: 残り 1 の注文で filler_charge を半分にする）

注文処理の将来費用に、残りの注文数（ホライズン R = 1024）を入れる予備実験。

- main が各注文の前に `solver.set_horizon(R - 1 - r)` を呼ぶ（残りの注文数）。
- 最後の注文（残り 0）では plan_cost を手数だけにする（filler_charge、adaptive_next_cost、generic_bias を 0 倍）。次の注文がないので、古い穴埋め紙の返却（fret）や返却先の深さの費用は払う必要がない。近似の補正（tie_choice）も最後の注文では行わない。
- 残り 1 の注文では filler_charge を `HORIZON_F1`（既定 1.0 = 変更なし）倍にする。最後の注文で穴埋め紙を戻す必要があるのは表示を妨げる場合だけなので、返却の確率 0.7 は過大。
- それ以外の注文では出力は dcomp-combo-dual30 と同一（倍率 1.0 の掛け算は厳密）。

評価は `--design-from` で設計を固定して注文処理だけを比べる。
