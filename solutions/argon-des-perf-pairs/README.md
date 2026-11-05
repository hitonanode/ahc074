改良元: solutions/esw-slim

D2の時間超過を許す測定版。基準のhead穿孔後、同色の上位3候補を扱う。
非head露出率0.25（ARGON_D2_RATE）、追加段は64標本（ARGON_D2_SAMPLES）。
単独穴の追加後、同じ非head紙のハンドル2個を同時に反転する近傍を全列挙する。
単独穴では利益がなくても、2穴で長い範囲を覆える相乗効果を調べる。
紙自身の追加表示費用、他の紙の目標への効用、区間DPの重なりを同時評価する。

スイッチと指標はargon-des-perforationと同じ。d2_single_netは単独穴後の予測差、
d2_pair_acceptsは2穴同時近傍の受理回数。既存ログ等は保持。
時間制限を超える場合は測定専用として--no-recordで実行する。
共通の検証報告はsolutions/argon-des-perforation/REPORT.md。
