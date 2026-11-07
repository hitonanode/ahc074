# deval-smallmoves

改良元: solutions/deval-climbcache。

注文計画の操作列を、通常の16操作まではオブジェクト内に持つ。長い列は動的vectorへ移すので、操作数の上限や探索結果は変えない。保存状態・メモ・後処理候補の操作列の短いコピーでヒープ確保を減らす。append、縮小、clear後の再利用を含めてvectorと照合する。

設計・注文の探索回数は親と同じ。時間不足による切替えはない。ログ、DesignStore、@paper/@ops、目次と段の目印を維持。
