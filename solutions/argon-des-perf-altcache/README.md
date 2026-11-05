改良元: solutions/argon-des-perf-latew105

穿孔を反映した再割当の後に、全ての新しい列頭を対象として穿孔をもう一度行う。
現在の共有目標が両方同じ色を要求する窓だけを復元でき、新しい穴も許す。
既存の穴は非headでも復元候補に含める。自列ハンドル・汎用窓・capは変えない。
再評価の係数は0.7、32層化標本。ARGON_D2_ALT_PASSESの既定値は1（0で追加段を無効化）。
層化乱数は窓数と固定seedだけで決まるため、初回に作った一様乱数を再利用する。
再評価の値や候補順を変えず、乱数生成の重複を省く。

d2_alt_trials/acceptsは候補数/採用数、before/after/added/restoredは穴数、
cost/owner/donorは注文当たりの穴費用/所有目標の条件付き価値/他目標への価値の差。
build_sec/search_secは再評価の準備/探索時間、sec/end_secは段の時間/終了時刻。
全既存ログ・スイッチ・プロファイラ・DesignStoreを保持する。
design_papers: alternating perforation and reassignment の段と目次項目を追加する。
