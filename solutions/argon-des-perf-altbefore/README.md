改良元: solutions/argon-des-perf-latew105

交互穿孔の順序を調べる対照。初回穿孔の直後にhead・色確率を更新し、
新しい穴と復元を許す2回目の穿孔を行い、その後に既存の穿孔後再割当を1回行う。
これにより「再割当への適応」と「初回穿孔の穴への再適応」を切り分ける。
係数0.7、32層化標本。ARGON_D2_ALT_PASSES既定1。一様乱数を再利用する。
d2_alt_*指標はaltcacheと同じ。既存ログ・スイッチ・プロファイラ・DesignStoreを保持。
追加段design_papers: alternating perforation and reassignmentを
perforation-aware reassignmentの前に置き、目次も対応させる。
