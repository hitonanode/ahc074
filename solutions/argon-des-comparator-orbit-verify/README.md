改良元: solutions/argon-des-perf-stratacut

距離表を紙番号の置換で作るargon-des-comparator-orbitの検査版。
元の全始点BFSも独立に実行し、距離表の全要素が一致することをassertで確かめる。
argon_distance_verifiedは照合した要素数。検査後も通常の設計・注文処理を行う。
この余分な検査の時間は高速化の比較には使わない。全ログ・profiler・スイッチを維持する。
