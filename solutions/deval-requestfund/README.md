# deval-requestfund

改良元: solutions/deval-climbcache。

追加した出力保存の高速化: なし。各変更の内容は対応する deval-* のREADMEと ../deval-speed/make_*.py に記載。生成手順は ../deval-speed/compose.py。

注文探索の固定設定: REPEAT_MIN=.05, POST_CANDIDATES=5。明示的なF3_*環境変数は実験用の上書きとして使える。LOCAL_BENCHで時間に応じて予算を変えない。

STATE.md 07:20に従い、時間不足による探索削減は置かない。 DesignStore・@paper/@ops・目次と段の目印を維持する。
