# ejectの表示再構成を短縮する実験

削除する2操作が作る積層を、不変区間ごとの上位色と所有窓から合成する版を作った。表示フィルタを通る候補だけで完全なorderを構築する。

固定設計500×2。`20261106-122751_nogen-distance-rename` / `20261106-122945_nogen-eject-segments` はstdout1000本同一、req_secは0.590618→0.604613秒と遅く不採用。所有窓を持つ紙だけの疎な区間へ変えた `20261106-123225_nogen-eject-segments2` も、基準 `20261106-123213_nogen-distance-rename` に対し全件同点、req_sec 0.590631→0.594634秒と遅かった。

別の単純版 `nogen-eject-lazyorder` は元の走査を残し、order/position構築だけを遅延した。初版 `20261106-123647_nogen-eject-lazyorder` はorder構築の削除範囲を誤りWA。修正後の `20261106-124442_nogen-distance-rename` / `20261106-124449_nogen-eject-lazyorder` を16×2から500×2へ延長し、1000本のstdout同一、WA0を確認した。req_sec 0.586217→0.595920秒で、これも不採用。現在のソースは修正版。
