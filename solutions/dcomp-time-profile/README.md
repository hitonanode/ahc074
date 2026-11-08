改良元: solutions/dcomp-combo-dual30

設計の段の境界だけで時刻を読み、窓探索・gopt・初期マッチング・共有annealと4分岐の各区間・候補ごとのfiller/Hungarian/穴あけ/後段再割当/V・初期列順・helper準備を計測する。探索の回数、乱数、採用規則、要求処理は変更しない。

`dt_<段>_sec`は所要時間、`_begin`/`_end`は倍率込みプログラム時刻。`c0`から`c8`は設計候補の番号。`design_total`は設計全体で、個別の段と重なる集計値。境界時計以外の追加計測はない。全てscaled_since経由でCLOCK_SCALEを適用する。

設計計測後に32768回の時計読みを測り、`dt_clock_ns`へ1回あたりの平均費用を出す。この校正分は設計の個別段には含まれず、helper_endには含まれる。
