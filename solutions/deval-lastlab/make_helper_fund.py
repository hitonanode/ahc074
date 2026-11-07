from merge_exact import *
s=delta(read('deval-equalfund-fast'),read('deval-trim6b'),read('deval-canonicalstamp6'))
changes=[('''                // The four independent necessary-condition tests use the same exact
                // integer masks. Masked gathers never read an unstamped owned entry.
                // Surviving papers are still visited in the original ascending order.
''','''                // Exact four-lane tests; gather stamped owners, visit survivors in order.
'''),('''        // Compact the same byte subsequence in blocks; the table preserves lane order.
        // The general scalar path also supports a design with other non-column IDs.
''','''        // Pack the same key in lane order; unusual role maps use the scalar path.
'''),('''        // Even stamps mark this pass; the low bit records an old filler.
        // Clearing the K-entry maps is needed only at unsigned wraparound.
''','''        // Even epoch is current; its low bit marks old fillers. Clear only on wrap.
'''),('''        // single helpers: at most 5 deep in their column, fewer generic moves than without; the 6 of
        // least distance + depth + 1.8 + digs of the handle holes they do not cover
''','''        // Helpers of depth <=5: rank by generic distance + depth + 1.8 + remaining fixes.
''')]
for a,b in changes:
 assert s.count(a)==1,a;s=s.replace(a,b)
s=s.replace('CF_SCOPE(single_helper);  // the nearest goal (deeper on ties)','CF_SCOPE(single_helper);  // nearest goal, then future cost, then depth')
info='''穴あけ前rematchを最初4枝で2回から1回に減らし、注文候補へ時間を移す。完成8設計からVで選ぶ。単独helperには通常と同じgeneric移動数の候補も見積り上位1件まで許し、従来のstrict候補と合わせて上位3件を実行する。同距離のgeneric goalは、既存の1注文先futureが小さい方を選ぶ。

NEUTRAL_WIDTH=4、NS_ROUNDS=2、PLAN_SHORTLIST=6。現計画以下の手数に加え、1手長い計画もraw plan_costの差が1.5以下なら後処理する。各予算は固定し、窓割当て・焼きなまし・候補数に時刻での切替えはない。

出力を保つ変更は、eject必要条件の整数AVX2検査、cache keyのSSE圧縮、canonicalizeの世代stampである。浮動小数点の順序・候補順を保つ。stampの下位bitは旧fillerの優先順を記録し、元の記録に重複があっても同じ再構成を行う。呼出しのないVのfeature export2メソッドと古いコメントを削除し、新規コメントを簡潔にした。

DesignStoreは選んだ設計を保存する。dv_candidates/dv_chosenは設計選択、dv_finish_secは仕上げ累計、req_sec/end_secはCLOCK_SCALE付きの注文時間/終了時刻。元の@paper/@ops、ログ、trace、profiler、全実験switch、段の目次を保つ。'''
emit('deval-helper-fund','deval-equalfund-fast',s,info)
emit('deval-helper-gap1','deval-helper-fund',s.replace('c.cost <= baseline_value + 1.5','c.cost <= baseline_value + 1.0'),info.replace('差が1.5以下','差が1.0以下'))
