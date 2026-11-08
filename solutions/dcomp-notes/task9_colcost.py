"""Do not recompute unchanged quadratic column costs for single/single swaps."""
from pathlib import Path

root=Path(__file__).resolve().parents[2]
s=(root/'solutions/dcomp-nine/main.cpp').read_text()
a='''            const __m128i costs = colcost_pair(_mm_setr_epi32(cnc[P] + dnc[0], cnc[Q] + dnc[1], 0, 0),
                                               _mm_setr_epi32(cnt[P] + dnt[0], cnt[Q] + dnt[1], 0, 0),
                                               _mm_setr_epi32(cn1[P] + dn1[0], cn1[Q] + dn1[1], 0, 0),
                                               _mm_setr_epi32(cp1[P] + dp1[0], cp1[Q] + dp1[1], 0, 0));
            const int cvP = _mm_cvtsi128_si32(costs), cvQ = _mm_extract_epi32(costs, 1);'''
b='''            int cvP,cvQ;
            if(sy==1 && !px && !py) {
                // Exchanging two singles keeps nc, nt and pairOne unchanged.
                // Only the monochromatic-column penalty can change. Include
                // the old penalty too, so this identity holds for every state.
                const int a=cn1[P]+dn1[0],b=cn1[Q]+dn1[1];
                cvP=cv[P]+4000000*(int(a==0||a==cnc[P])-int(cn1[P]==0||cn1[P]==cnc[P]));
                cvQ=cv[Q]+4000000*(int(b==0||b==cnc[Q])-int(cn1[Q]==0||cn1[Q]==cnc[Q]));
            } else {
                const __m128i costs=colcost_pair(_mm_setr_epi32(cnc[P]+dnc[0],cnc[Q]+dnc[1],0,0),
                    _mm_setr_epi32(cnt[P]+dnt[0],cnt[Q]+dnt[1],0,0),
                    _mm_setr_epi32(cn1[P]+dn1[0],cn1[Q]+dn1[1],0,0),
                    _mm_setr_epi32(cp1[P]+dp1[0],cp1[Q]+dp1[1],0,0));
                cvP=_mm_cvtsi128_si32(costs);cvQ=_mm_extract_epi32(costs,1);
            }'''
assert s.count(a)==1
p=root/'solutions/dcomp-nine-singlecost';p.mkdir(exist_ok=True)
(p/'main.cpp').write_text(s.replace(a,b))
(p/'README.md').write_text('''改良元: solutions/dcomp-nine

annealでsingle同士の列交換をする場合、各列の紙数・target数・共有ペアの色数は不変なので、列費用の二次式を再計算しない。変わり得る単色列ペナルティの差だけを加える。元が単色だった場合も引くので、すべての状態で元の整数式と等しい。それ以外の移動は既存のSIMD式を使う。

穴費用の浮動小数点演算、受理と乱数列、固定反復数、9候補、注文処理、CLOCK_SCALE、ログ、実験スイッチ、プロファイラを保つ。時間不足の切替なし。
''')
