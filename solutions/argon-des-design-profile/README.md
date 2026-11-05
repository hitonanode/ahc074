改良元: solutions/argon-des-perf-stratacut

既存のAF_PROFILEを既定で有効にした計測版。設計の内容、乱数、反復予算、注文処理は変えない。
af_*_calls / af_*_samples / af_*_secで設計焼きなまし、フィラー、再割当、穿孔、補助表の内訳を調べる。
サンプル計測のオーバーヘッドを含むため、採用版の時間判定には用いない。
全ログ・スイッチ・CLOCK_SCALE・LOCAL_BENCH・DesignStore・段の目印と目次を保持する。
