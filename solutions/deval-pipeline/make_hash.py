from pathlib import Path
P=Path(__file__).resolve().parent;R=P.parents[1]
b=(R/'solutions/deval-ordered8/main.cpp').read_text()
helper='''
// Hash is only an index: every cache still compares its complete exact key.
inline u64 parallel_key_hash(const uint8_t* bytes,int length,u64 seed) {
    u64 a=seed,b=0x9e3779b97f4a7c15ULL,c=0xbf58476d1ce4e5b9ULL,d=0x94d049bb133111ebULL;
    constexpr u64 prime=0x100000001b3ULL;
    int i=0;
    for(;i+32<=length;i+=32) {
        u64 w[4];std::memcpy(w,bytes+i,32);
        a=(a^w[0])*prime;b=(b^w[1])*prime;c=(c^w[2])*prime;d=(d^w[3])*prime;
    }
    a^=std::rotl(b,13)^std::rotl(c,29)^std::rotl(d,47);
    for(;i+8<=length;i+=8){u64 w;std::memcpy(&w,bytes+i,8);a=(a^w)*prime;}
    return a;
}
'''
next_old='''        u64 hash = 0xcbf29ce484222325ULL ^ key_size;
        for (int i = 0; i < padded; i += 8) {
            u64 word;
            std::memcpy(&word, key.data() + i, 8);
            hash = (hash ^ word) * 0x100000001b3ULL;
        }'''
end_old='''                    u64 hash = 0xcbf29ce484222325ULL;
                    for (int j = 0; j + 8 <= K; j += 8) {
                        u64 word;
                        std::memcpy(&word, next.data() + j, 8);
                        hash = (hash ^ word) * 0x100000001b3ULL;
                    }'''
assert next_old in b and end_old in b
for name,next_,end_ in [('deval-hash-next',True,False),('deval-hash-end',False,True),('deval-hash-both',True,True)]:
 s=b.replace('// ==== Request profiling (COLFAST_PROFILE): inclusive and exclusive times ====',helper+'\n// ==== Request profiling (COLFAST_PROFILE): inclusive and exclusive times ====',1)
 if next_:s=s.replace(next_old,'        u64 hash=parallel_key_hash(key.data(),padded,0xcbf29ce484222325ULL^key_size);',1)
 if end_:s=s.replace(end_old,'                    u64 hash=parallel_key_hash(next.data(),K,0xcbf29ce484222325ULL);',1)
 p=R/'solutions'/name;p.mkdir();(p/'main.cpp').write_text(s)
 (p/'README.md').write_text('改良元: `solutions/deval-ordered8`。\n\n'+('列の次状態価値キャッシュ' if next_ else '')+('と' if next_ and end_ else '')+('後処理の最終状態キャッシュ' if end_ else '')+'のハッシュを4本の独立した整数演算で計算する。キー全体の完全一致照合と保存する評価値は同じ。ハッシュ衝突は置換を起こすだけで、異なる状態の値を使わない。浮動小数点の演算、探索設定と候補順は保つ。\n')
 print(name,len(s.encode()))
