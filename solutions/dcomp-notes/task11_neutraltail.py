from pathlib import Path
R=Path(__file__).resolve().parents[2];B=(R/'solutions/dcomp-combo-alt1/main.cpp').read_text()
def write(name,s,desc):
 d=R/'solutions'/name;assert not d.exists();d.mkdir();(d/'main.cpp').write_text(s)
 (d/'README.md').write_text('改良元: solutions/dcomp-combo-alt1\n\n'+desc+'\n\n両コンパイラの固定探索予算を共用。ログ・trace・profiler・実験スイッチ・目次と段・DesignStoreを保持し、時計分岐なし。\n')
a='if (moves < best_tail.moves) best_tail = {k1, anc1, k2, anc2, moves};';assert B.count(a)==1
write('dcomp-t11-tailorder',B.replace(a,a.replace('moves <','moves <=')).replace('// Try g then f before f then g; ties keep the former.','// Try both legal move orders; equal lengths keep f then g for later repair diversity.'),'2→2中立修復の二つの移動順が同じ操作数で合法なら、後の順を選ぶ。同じ完成stackでも操作順が異なると次のpost修復の近傍が変わるため、追加の候補評価なしで比較する。')
a='''                        for (int gap = 0; gap < gap_count; gap++) {
                            const auto [a, b] = gap_pairs[gap];''';assert B.count(a)==1
s=B.replace(a,'''                        for (int gap = 0; gap < gap_count; gap++) {
                            // The identical endpoint pair produces the identical edits and replay.
                            // It cannot add a different neutral signature or improve its own value.
                            if(gap==1 && gap_pairs[1]==gap_pairs[0])continue;
                            const auto [a, b] = gap_pairs[gap];''')
write('dcomp-t11-taildedup',s,'中立修復の浅い端と深い端が同じgap組のとき、二度目の同一操作列評価を省く。候補順・実数計算は同じ。exact cacheのhit/missと試行回数counterだけは変わり得る。出力一致を両コンパイラで検証する。')
