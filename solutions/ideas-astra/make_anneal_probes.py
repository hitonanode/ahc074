from pathlib import Path
root=Path(__file__).resolve().parents[2]
base=(root/'solutions/dcomp-combo-dual30/main.cpp').read_text()
def sub(s,a,b):
 assert s.count(a)==1,(s.count(a),a[:100])
 return s.replace(a,b)
def write(name,s,desc):
 p=root/'solutions'/name;p.mkdir(exist_ok=False)
 (p/'main.cpp').write_text(s)
 (p/'README.md').write_text('改良元: solutions/dcomp-combo-dual30。\n\n'+desc+'\n\n乱数列、費用式、固定反復数、候補順、DesignStore、属性出力を保つ。出力同一性とGCC/Clangの時間を小さなprobeで調べるための試作で、最終版ではない。\n')
s=base
s=sub(s,'            const int cvx = _mm_cvtsi128_si32(costs), cvy = iy ? _mm_extract_epi32(costs, 1) : 0;','''            const int cvx = _mm_cvtsi128_si32(costs), cvy = iy ? _mm_extract_epi32(costs, 1) : 0;
            // The monochromatic-column penalty exceeds every possible hole/generic
            // gain and anneal threshold. Keep accept(positive)'s one RNG draw.
            if (((cvx - cv[cx]) + (iy ? cvy - cv[cy] : 0)) > 400000) {
                D.rng.next();
                return;
            }''')
s=sub(s,'            double dg = 0;\n            for (int i = 0; i < k; i++) dg += D.gc(nu[i]) - D.gc(D.unit[xs[i]]);','''            // At most three units change; their generic cost is far smaller than
            // the 10000 bound used for an impossible column, as are all hole costs.
            if (dcol > 400000) { D.rng.next(); return; }
            double dg = 0;
            for (int i = 0; i < k; i++) dg += D.gc(nu[i]) - D.gc(D.unit[xs[i]]);''')
a='''            int tot = 0;
            float mb_old1'''
b='''            const __m128i costs =
                colcost_pair(_mm_setr_epi32(cnc[a], cnc[b], 0, 0), _mm_setr_epi32(cnt[a], cnt[b], 0, 0),
                             _mm_setr_epi32(n1a, n1b, 0, 0), _mm_setr_epi32(pa, pb, 0, 0));
            const int cva = _mm_cvtsi128_si32(costs), cvb = _mm_extract_epi32(costs, 1);
            if ((cva + cvb) - (cv[a] + cv[b]) > 400000) { D.rng.next(); return; }
            int tot = 0;
            float mb_old1'''
old='''            const __m128i costs =
                colcost_pair(_mm_setr_epi32(cnc[a], cnc[b], 0, 0), _mm_setr_epi32(cnt[a], cnt[b], 0, 0),
                             _mm_setr_epi32(n1a, n1b, 0, 0), _mm_setr_epi32(pa, pb, 0, 0));
            const int cva = _mm_cvtsi128_si32(costs), cvb = _mm_extract_epi32(costs, 1);
'''
s=sub(s,old,'');s=sub(s,a,b)
write('ia-anneal-reject',s,'column_moveに既存の「列から一方の色が消えるなら必ず棄却」の判定を、target_move、multi_move、handle_swapにも適用する。正確な列費用の増加が10000を超える場合のみ、元のacceptが消費する乱数1回を消費して重い穴費用の評価を省く。色が消えない手の受理規則は変えない。')
s=sub(base,'if (r == NR - 1 && !((dirty >> (8 * r)) & 255))','if (!((dirty >> (8 * r)) & 255))')
write('ia-dirty-groups',s,'annealの穴費用評価で、従来は最後のSIMD群だけ省略した変更なし群を、全SIMD群で省く。整数カウント・元の四則演算・加算の順を保ち、変更なしのQを保存値から読む。分岐追加と除算削減の差し引きを測る。')
