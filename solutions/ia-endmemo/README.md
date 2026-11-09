# ia-endmemo

改良元: `solutions/dcomp-combo-dual30`。

後処理の終状態メモを、1 回の post_optimize_impl 内から同じ注文内の複数回へ広げる試作。canonicalize が参照する旧 filler の紙 ID と優先順を完全一致で照合し、同じ順のときだけ世代を共用する。最終 192 枚の紙順も既存どおり完全一致で照合する。可視性の再生は省かない。

設計、候補の列挙順、費用の加算順、探索回数は変更しない。`IA_ENDMEMO_SIZE` は表の件数（既定 128、2 の冪）。`IA_ENDMEMO_CHECK` は hit で元の canonicalize・費用を計算し直し、完全一致を検査する確認用ビルド。

指標: `ia_endmemo_context_reuse/new` は同じ旧 filler 順を再利用/初出した post 回数、`ia_endmemo_cross_hits` は別 post 呼び出しの結果へ hit した回数、`ia_endmemo_cross_reachable` はそのうち filler が到達可能だった数。既存の `f2_memo_hits/misses` も維持する。操作属性・ラベルは親と同じ。
