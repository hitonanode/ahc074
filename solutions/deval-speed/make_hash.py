from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
s=(ROOT/'solutions/deval-vbranch-o3/main.cpp').read_text()
idx=s.index('    double adaptive_next_cost(const GenericSplit& split) const {')
s=s[:idx]+'''    // Four independent chains avoid a long serial multiply dependency.
    // Full keys are still compared, so this changes replacement policy only.
    static u64 cache_hash(const uint8_t* bytes,int count,u64 seed) {
        u64 a=seed,b=seed^0x9e3779b97f4a7c15ULL,c=~seed,d=seed^0xd1b54a32d192ed03ULL;
        int i=0;
        for(;i+32<=count;i+=32) {
            u64 w0,w1,w2,w3;
            std::memcpy(&w0,bytes+i,8);std::memcpy(&w1,bytes+i+8,8);
            std::memcpy(&w2,bytes+i+16,8);std::memcpy(&w3,bytes+i+24,8);
            a=(a^w0)*0x100000001b3ULL;b=(b^w1)*0x100000001b3ULL;
            c=(c^w2)*0x100000001b3ULL;d=(d^w3)*0x100000001b3ULL;
        }
        a^=std::rotl(b,13)^std::rotl(c,27)^std::rotl(d,41);
        for(;i<count;i+=8){u64 word;std::memcpy(&word,bytes+i,8);a=(a^word)*0x100000001b3ULL;}
        return a;
    }
'''+s[idx:]
old='''        u64 hash = 0xcbf29ce484222325ULL ^ key_size;
        for (int i = 0; i < padded; i += 8) {
            u64 word;
            std::memcpy(&word, key.data() + i, 8);
            hash = (hash ^ word) * 0x100000001b3ULL;
        }'''
assert old in s
s=s.replace(old,'''        u64 hash = cache_hash(key.data(),padded,0xcbf29ce484222325ULL ^ key_size);''',1)
old='''                    u64 hash = 0xcbf29ce484222325ULL;
                    for (int j = 0; j + 8 <= K; j += 8) {
                        u64 word;
                        std::memcpy(&word, next.data() + j, 8);
                        hash = (hash ^ word) * 0x100000001b3ULL;
                    }'''
assert old in s
s=s.replace(old,'''                    u64 hash = cache_hash(next.data(),K,0xcbf29ce484222325ULL);''',1)
d=ROOT/'solutions/deval-hash4';d.mkdir(exist_ok=True)
(d/'main.cpp').write_text(s)
(d/'README.md').write_text('''# deval-hash4

改良元: solutions/deval-vbranch-o3。

注文の最終状態・翌注文費用キャッシュで、キーのハッシュを4本の独立した整数列で計算する。完全キーの照合を維持するため、衝突はキャッシュの置換だけに影響する。値の演算と探索順は同じ。予算・時間ガードは変更しない。
''')
print(len(s.encode()))
