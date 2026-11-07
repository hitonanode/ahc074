from pathlib import Path
P=Path(__file__).resolve().parent;root=P.parents[1]
s=(root/'solutions/deval-trim6b/main.cpp').read_text()
a='    double adaptive_next_cost(const GenericSplit& split) const {'
assert s.count(a)==1
s=s.replace(a,'    __attribute__((target("ssse3,sse4.1,popcnt"))) double adaptive_next_cost(const GenericSplit& split) const {')
a='        for (int k : order) if (col_of[k] >= 0 && !extra[k]) key[key_size++] = k;'
b='''        // Compact the same byte subsequence in blocks; the table preserves lane order.
        // The general scalar path also supports a design with other non-column IDs.
        static const auto shuffle=[] {
            std::array<std::array<uint8_t,16>,256> t{};
            for(int mask=0;mask<256;++mask){t[mask].fill(128);int at=0;
                for(int j=0;j<8;++j)if(mask>>j&1)t[mask][at++]=j;}
            return t;
        }();
        bool ordinary=true;
        for(int k=0;k<K;++k)if((col_of[k]>=0)!=(k>kCapPaper)){ordinary=false;break;}
        if(ordinary) {
            for(int i=0;i<K;i+=16) {
                const __m128i v=_mm_loadu_si128((const __m128i*)(order.data()+i));
                __m128i excluded=_mm_cmpeq_epi8(_mm_min_epu8(v,_mm_set1_epi8(kCapPaper)),v);
                if(top_d>=0)excluded=_mm_or_si128(excluded,_mm_cmpeq_epi8(v,_mm_set1_epi8(top_d)));
                for(const auto& f:fillers)excluded=_mm_or_si128(excluded,_mm_cmpeq_epi8(v,_mm_set1_epi8(f.paper)));
                const unsigned mask=~_mm_movemask_epi8(excluded)&65535;
                const unsigned lo=mask&255,hi=mask>>8;
                _mm_storel_epi64((__m128i*)(key.data()+key_size),_mm_shuffle_epi8(v,_mm_loadu_si128((const __m128i*)shuffle[lo].data())));
                key_size+=__builtin_popcount(lo);
                _mm_storel_epi64((__m128i*)(key.data()+key_size),_mm_shuffle_epi8(_mm_srli_si128(v,8),_mm_loadu_si128((const __m128i*)shuffle[hi].data())));
                key_size+=__builtin_popcount(hi);
            }
        } else for(int k:order)if(col_of[k]>=0 && !extra[k])key[key_size++]=k;'''
# Avoid checking the fixed role map on each call.
s=s.replace('    std::vector<double> depth_terms;','    std::vector<double> depth_terms;\n    bool key_roles_ordinary=false;')
a0='        depth_terms.resize(K * stride);'
assert s.count(a0)==1;s=s.replace(a0,a0+'\n        key_roles_ordinary=true;\n        for(int k=0;k<K;++k)if((col_of[k]>=0)!=(k>kCapPaper))key_roles_ordinary=false;')
b=b.replace('        bool ordinary=true;\n        for(int k=0;k<K;++k)if((col_of[k]>=0)!=(k>kCapPaper)){ordinary=false;break;}\n        if(ordinary)', '        if(key_roles_ordinary)')
assert s.count(a)==1;s=s.replace(a,b)
p=root/'solutions/deval-keypack6';p.mkdir();(p/'main.cpp').write_text(s);assert len(s.encode())<=522000
(p/'README.md').write_text('''改良元: `solutions/deval-trim6b`。

adaptive_next_costのcache keyを作る走査を、16 byteずつの整数SIMDと8 byte圧縮tableに変える。非column紙・top_d・fillersを除いた紙番号は元の順に保存し、hash・完全一致検査・浮動小数点計算は変えない。roleが通常の番号配置でない設計には元の走査を使う。これは設計形式による分岐であり時間で探索を変えない。ログ・統計・profiler・実験switchを保つ。\n''');print(len(s.encode()))
