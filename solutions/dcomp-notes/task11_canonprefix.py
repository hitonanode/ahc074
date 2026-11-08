from pathlib import Path
R=Path(__file__).resolve().parents[2];B=(R/'solutions/dcomp-combo-alt1/main.cpp').read_text()
begin=B.index('    void canonicalize() {');end=B.index('    struct State {',begin)
old=B[begin:end]
part=old.replace('    void canonicalize() {','    __attribute__((target("avx2"))) void canonicalize() {',1)
lo=part.index('        int cur = H, ntop = -1, nf_count = 0;');hi=part.index('        std::reverse(nf.begin()',lo)
part=part[:lo]+r'''        int ntop=-1,nf_count=0,minimum=H;
#ifdef CANON_PREFIX_CHECK
        const int before_top=top_d;const auto before_fillers=fillers;
#endif
        const auto shift1=_mm256_setr_epi32(0,0,1,2,3,4,5,6);
        const auto shift2=_mm256_setr_epi32(0,0,0,1,2,3,4,5);
        const auto shift4=_mm256_setr_epi32(0,0,0,0,0,1,2,3);
        const auto ceiling=_mm256_set1_epi32(H),negative=_mm256_set1_epi32(-1);
        const auto reverse=_mm_setr_epi8(7,6,5,4,3,2,1,0,-128,-128,-128,-128,-128,-128,-128,-128);
        for(int hi=K;hi>0;hi-=8) {
            const auto bytes=_mm_shuffle_epi8(_mm_loadl_epi64((const __m128i*)(order.data()+hi-8)),reverse);
            const auto ids=_mm256_cvtepu8_epi32(bytes);
            const auto columns=_mm256_i32gather_epi32(col_of.data(),ids,4);
            const auto normal=_mm256_cmpgt_epi32(columns,negative);
            const auto generic=_mm256_cmpgt_epi32(_mm256_set1_epi32(M),ids);
            // A generic sheet makes every later column paper out of place. The
            // cap and other non-column sheets leave the running minimum alone.
            const auto code=_mm256_blendv_epi8(ceiling,columns,_mm256_or_si256(normal,generic));
            auto mins=code;
            mins=_mm256_min_epi32(mins,_mm256_blend_epi32(ceiling,_mm256_permutevar8x32_epi32(mins,shift1),0xfe));
            mins=_mm256_min_epi32(mins,_mm256_blend_epi32(ceiling,_mm256_permutevar8x32_epi32(mins,shift2),0xfc));
            mins=_mm256_min_epi32(mins,_mm256_blend_epi32(ceiling,_mm256_permutevar8x32_epi32(mins,shift4),0xf0));
            mins=_mm256_min_epi32(mins,_mm256_set1_epi32(minimum));
            const auto previous=_mm256_blend_epi32(_mm256_set1_epi32(minimum),_mm256_permutevar8x32_epi32(mins,shift1),0xfe);
            const unsigned fresh=_mm256_movemask_ps(_mm256_castsi256_ps(_mm256_and_si256(normal,_mm256_cmpgt_epi32(previous,mins))));
            const unsigned outside=_mm256_movemask_ps(_mm256_castsi256_ps(_mm256_and_si256(normal,_mm256_cmpgt_epi32(code,mins))));
            alignas(32) int cc[8],mm[8];
            _mm256_store_si256((__m256i*)cc,columns);_mm256_store_si256((__m256i*)mm,mins);
            // A column first becomes nonempty exactly when the minimum decreases
            // to it. Equal later papers need no repeated store to nonempty[c].
            for(unsigned bits=fresh;bits;bits&=bits-1)nonempty[cc[__builtin_ctz(bits)]]=1;
            for(unsigned bits=outside;bits;bits&=bits-1) {
                const int lane=__builtin_ctz(bits),i=hi-1-lane,k=order[i],c=cc[lane];
                if(i==0 || (i==1 && order[0]==kCapPaper))ntop=k;
                else nf[nf_count++]={k,std::max(0,mm[lane]),c};
            }
            minimum=mm[7];
        }
'''+part[hi:]
needle='''        fillers.assign(res.begin(), res.begin() + res_count);
    }'''
assert part.count(needle)==1
part=part.replace(needle,'''        fillers.assign(res.begin(), res.begin() + res_count);
#ifdef CANON_PREFIX_CHECK
        const auto expected_fillers=fillers;const int expected_top=top_d;
        top_d=before_top;fillers=before_fillers;canonicalize_reference();
        if(top_d!=expected_top || !same_fillers(fillers,expected_fillers)) {
            std::cerr<<"CANON_PREFIX_MISMATCH\\n";std::abort();
        }
#endif
    }''')
s=B[:begin]+'#ifdef CANON_PREFIX_CHECK\n'+old.replace('void canonicalize()','void canonicalize_reference()',1)+'#endif\n'+part+B[end:]
for name,source,extra in [('dcomp-t11-canon-prefix',s,''),('dcomp-t11-canon-check','#define CANON_PREFIX_CHECK 1\n'+s,'元のscalar関数で全呼出しを再計算し、top_dと全filler記録の順序まで照合する検証版。')]:
 d=R/'solutions'/name;assert not d.exists();d.mkdir();(d/'main.cpp').write_text(source)
 (d/'README.md').write_text('改良元: solutions/dcomp-combo-alt1\n\ncanonicalizeのbottom-up scanを8紙ずつの整数prefix minimumへ置換する。generic紙を負の値、capをHとして扱うと、minより大きい列の紙だけが元のout-of-column紙になる。nonemptyはminが初めてその列へ下がる時だけ記録する。out紙の順序と後半の正規化は元のまま。'+extra+'\n\nprofileのcanonicalize段を対象とする。浮動小数・候補順・予算は変えない。両コンパイラでbyte一致を測る。ログ・trace・profiler・実験スイッチ・目次と段・DesignStoreを保持する。時計分岐なし。\n')
