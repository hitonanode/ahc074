from pathlib import Path
p=Path(__file__).resolve().parent
s=(p.parent/'eject-one/main.cpp').read_text()
s=s.replace('    static inline bool mid_once=true;', '    static inline bool lazy_positions=true;\n    long long position_builds=0;\n    static inline bool mid_once=true;')
old='''                    for(u64 z=two;z;z&=z-1)second[__builtin_ctzll(z)]=t;
                    for(u64 z=one;z;z&=z-1)first[__builtin_ctzll(z)]=t;'''
assert old in s
s=s.replace(old,'                    if(!lazy_positions){\n'+old+'\n                    }')
needle='                if(__builtin_popcountll(shown^A[u])<2)continue;'
s=s.replace(needle,'''                bool positions_ready=!lazy_positions;
                auto prepare_positions=[&]{
                    if(positions_ready)return;
                    positions_ready=true;position_builds++;
                    u64 covered=0,twice=0;
                    for(int t=0;t<K;t++){
                        int k=ord[t];u64 two=paper[k].opaque&covered&~twice,one=paper[k].opaque&~covered;
                        for(u64 z=two;z;z&=z-1)second[__builtin_ctzll(z)]=t;
                        for(u64 z=one;z;z&=z-1)first[__builtin_ctzll(z)]=t;
                        covered|=paper[k].opaque;twice|=two;if(twice==~u64(0))break;
                    }
                };
'''+needle)
needle='                    int pos=std::find(ord.begin(),ord.end(),k)-ord.begin(),lo=0,hi=K-1;'
assert needle in s
s=s.replace(needle,'                    prepare_positions();\n'+needle)
(p/'main.cpp').write_text(s)
