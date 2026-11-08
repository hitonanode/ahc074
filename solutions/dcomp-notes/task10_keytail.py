from pathlib import Path
r=Path(__file__).resolve().parents[2];base=(r/'solutions/dcomp-screen-replay/main.cpp').read_text()
for mode in ['tail','blocks']:
 s=base
 a='''        if (top_d >= 0) extra[top_d] = true;
        for (auto f : fillers) extra[f.paper] = true;
        std::array<uint8_t, 3 * K + 8> key;'''
 b='''        int excluded_total=kCapPaper+1;
        if (top_d >= 0) {extra[top_d]=true;excluded_total+=top_d>kCapPaper;}
        for (auto f : fillers) {
            excluded_total+=f.paper>kCapPaper && !extra[f.paper];extra[f.paper]=true;
        }
        std::array<uint8_t, 3 * K + 8> key;'''
 assert s.count(a)==1;s=s.replace(a,b)
 a='''                const unsigned lo=mask&255,hi=mask>>8;'''
 b='''                const unsigned lo=mask&255,hi=mask>>8;'''
 if mode=='blocks':b='''                if(mask==65535) {
                    _mm_storeu_si128((__m128i*)(key.data()+key_size),v);key_size+=16;
                } else {
'''+b
 assert s.count(a)==1;s=s.replace(a,b)
 a='''                key_size+=__builtin_popcount(hi);
            }
        } else for(int k:order)if(col_of[k]>=0 && !extra[k])key[key_size++]=k;'''
 b='''                key_size+=__builtin_popcount(hi);
'''+('                }\n' if mode=='blocks' else '')+'''                // order is a permutation. Once all excluded IDs have been seen,
                // the untouched suffix belongs verbatim to this same cache key.
                if(i+16-key_size==excluded_total) {
                    const int remaining=K-i-16;
                    std::memcpy(key.data()+key_size,order.data()+i+16,remaining);
                    key_size+=remaining;break;
                }
            }
        } else for(int k:order)if(col_of[k]>=0 && !extra[k])key[key_size++]=k;'''
 assert s.count(a)==1;s=s.replace(a,b)
 p=r/'solutions'/('dcomp-key-'+mode);assert not p.exists();p.mkdir();(p/'main.cpp').write_text(s)
 (p/'README.md').write_text('改良元: solutions/dcomp-screen-replay\n\nnext_costのcache keyの圧縮で、除外する7枚と、列外にある紙の重複しない総数を数える。走査済みの除外数が総数に達したら、残りはすべてkeyに入るためmemcpyする。keyの順序・全byte・hashと費用は不変。'+('全16枚が残る中間blockもshuffleせずに写す。' if mode=='blocks' else '')+'\n\n通常と異なる役割配置は元のscalar処理を保持する。予算、ログ・実験スイッチ・DesignStoreは維持、時間fallbackなし。\n')
