"""Replace two gathers in the eject mask screen with candidate-order storage."""
from pathlib import Path
R=Path(__file__).resolve().parents[2]
s=(R/'solutions/dcomp-combo-alt1/main.cpp').read_text()
a=s.index('    __attribute__((target("avx2"))) void eject_repairs(')
b=s.index('    // ==== Post-processing: two deletions and two repairs',a)
z=s[a:b]
def rep(old,new):
    global z
    assert z.count(old)==1,(z.count(old),old[:90]);z=z.replace(old,new)
rep('        std::array<u64, K> owned;',
'''        std::array<int,K> candidate_slot;candidate_slot.fill(-1);
        for(int ci=0;ci<candidate_count;++ci)candidate_slot[candidates[ci]]=ci;
        alignas(32) std::array<u64,K+4> candidate_owned;
#ifdef EJECT_OWNER_CHECK
        std::array<u64,K> reference_owned{};
#endif''')
rep('                trial_stamp++;',
'''                trial_stamp++;
                std::fill_n(candidate_owned.data(),(candidate_count+3)&~3,u64(0));
#ifdef EJECT_OWNER_CHECK
                reference_owned.fill(0);
#endif''')
rep('                        owned[k] = one;',
'''                        // Only candidate owners are ever read by the repair screen.
                        // A contiguous vector replaces per-lane stamp and ownership gathers.
                        if(one)if(const int ci=candidate_slot[k];ci>=0)candidate_owned[ci]=one;
#ifdef EJECT_OWNER_CHECK
                        reference_owned[k]=one;
#endif''')
rep('''                    const __m128i index=_mm_load_si128((const __m128i*)(candidates.data()+cb));
                    const __m128i stamps=_mm_i32gather_epi32(owner_stamp.data(),index,4);
                    const __m256i live=_mm256_cvtepi32_epi64(_mm_cmpeq_epi32(stamps,_mm_set1_epi32(trial_stamp)));
                    const __m256i own=_mm256_mask_i32gather_epi64(_mm256_setzero_si256(),(const long long*)owned.data(),index,live,8);''',
'''                    const __m256i own=_mm256_load_si256((const __m256i*)(candidate_owned.data()+cb));
#ifdef EJECT_OWNER_CHECK
                    for(int ci=cb;ci<std::min(cb+4,candidate_count);++ci)
                        if(candidate_owned[ci]!=reference_owned[candidates[ci]])std::abort();
#endif''')
s=s[:a]+z+s[b:]
for name,source in [('dcomp-t11-ownerpack',s),('dcomp-t11-ownercheck','#define EJECT_OWNER_CHECK 1\n'+s)]:
    p=R/'solutions'/name;assert not p.exists();p.mkdir();(p/'main.cpp').write_text(source)
    (p/'README.md').write_text('改良元: solutions/dcomp-combo-alt1\n\n2→1/1→1修復の各削除組について、最上位所有窓のmaskを修復候補の順番で保存する。候補以外の紙はこのmask判定で読まれない。候補の判定順、整数mask、可視性と得点評価は同じで、stampとownerの2回のgatherを1回の連続loadに置き換える。\n\n検証用EJECT_OWNER_CHECKでは元の紙番号別maskと全候補を照合する。探索予算は親と同じ、時計による変更はなく、既存ログ・trace・profiler・DesignStoreを保つ。\n')
