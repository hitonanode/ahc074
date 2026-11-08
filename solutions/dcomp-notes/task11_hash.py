from pathlib import Path
R=Path(__file__).resolve().parents[2];B=(R/'solutions/dcomp-combo-alt1/main.cpp').read_text()
def write(name,s,desc):
 d=R/'solutions'/name;assert not d.exists();d.mkdir();(d/'main.cpp').write_text(s)
 (d/'README.md').write_text('改良元: solutions/dcomp-combo-alt1\n\n'+desc+'\n\n設計・要求の固定予算、ログ・trace・profiler・実験スイッチ、目次と段、DesignStoreは保持する。時計による切替はない。\n')
x='''                    u64 hash = 0xcbf29ce484222325ULL;
                    for (int j = 0; j + 8 <= K; j += 8) {
                        u64 word;
                        std::memcpy(&word, next.data() + j, 8);
                        hash = (hash ^ word) * 0x100000001b3ULL;
                    }
                    hash = (hash ^ next[root]) * 0x100000001b3ULL;'''
assert B.count(x)==1
s=B.replace(x,'''                    // Four independent chains remove the long multiply dependency.
                    // This is only an index: the full successor array remains the collision check.
                    u64 h0=0xcbf29ce484222325ULL,h1=h0,h2=h0,h3=h0;
                    for(int j=0;j<K;j+=32) {
                        u64 w[4];std::memcpy(w,next.data()+j,32);
                        h0=(h0^w[0])*0x100000001b3ULL;h1=(h1^w[1])*0x100000001b3ULL;
                        h2=(h2^w[2])*0x100000001b3ULL;h3=(h3^w[3])*0x100000001b3ULL;
                    }
                    u64 hash=(h0 ^ (h1<<13|h1>>51) ^ (h2<<27|h2>>37) ^ (h3<<43|h3>>21));
                    hash=(hash^next[root])*0x9e3779b97f4a7c15ULL;''')
write('dcomp-t11-hash4',s,'終状態memoのindex用ハッシュを4本の独立したFNV鎖で計算する。後続配列193byte全体による衝突検査と、各経路の合法性再生は元通り。計算結果そのものは近似しない。')
s=B.replace(x,'''                    const u64 hash=end_hash(next);''')
pos='    std::array<EndMemo, 128> end_memo;';assert s.count(pos)==1
s=s.replace(pos,'''    __attribute__((target("avx2"))) static u64 end_hash(const Links& next) {
        __m256i h=_mm256_set1_epi32(int(2166136261U));
        const __m256i p=_mm256_set1_epi32(16777619);
        for(int j=0;j<K;j+=32)
            h=_mm256_mullo_epi32(_mm256_xor_si256(h,_mm256_loadu_si256((const __m256i*)(next.data()+j))),p);
        alignas(32) uint32_t lanes[8];_mm256_store_si256((__m256i*)lanes,h);
        u64 v=next[kRoot];
        for(int i=0;i<8;++i)v=(v^lanes[i])*0x100000001b3ULL;
        return v;
    }
'''+pos)
write('dcomp-t11-hash8',s,'終状態memoのindex用ハッシュを8本の32bit SIMD鎖で計算する。後続配列全体の衝突検査は保持し、hash一致だけで状態を共有しない。')
# A measured control for the cache's net value, still exposed via the existing switch.
import re
matches=list(re.finditer(r'memo[^\n]{0,80}',B));print([m.group() for m in matches[:8]])
write('dcomp-t11-design-prof','#define DESIGN_PROFILE 3\n#define AF_PROFILE 1\n'+B,'窓段の既存cycle profilerと設計anneal/finishingの既存sampling profilerを有効にした計測専用版。出力一致を親と確認する。計測の増分を含むため通常時間の比較には使わない。')
