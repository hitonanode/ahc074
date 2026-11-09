改良元: solutions/d30a-reset6

汎用層の下に残るfillerが次の注文の穴を覆う価値を、kCoverStrength=.50で見積もる。従来値0.25から増やし、reset6の設計での将来の修復費用に合わせる。kStayStrengthは0.25のまま。

通常実行の変更はこの定数だけ。固定反復回数、CLOCK_SCALE、DesignStore、既存ログと段目次を維持する。定数畳み込みを保つため実行時環境変数は追加しない。追加stderr指標なし。
