改良元: solutions/dcomp-combo-alt1

profileで約16msだったejectのfirst/second窓owner列挙、および修復部のbit列挙にBMIとpopcnt命令を許可する。整数のzero-bit消去・ctzを対象にし、FMAやfast-mathは追加しない。Clang nativeでは既に同等命令が使用可能なため差が小さい対照になる。

演算順・候補順・予算は変えない。ログ・trace・profiler・実験スイッチ・目次と段・DesignStoreを保持し、時計分岐なし。
