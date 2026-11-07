from pathlib import Path
P=Path(__file__).resolve().parent;root=P.parents[1]
s=(root/'solutions/deval-ejectsimd6/main.cpp').read_text()
a='''        int candidate_count = 0;
        for (int k = 0; k < K; k++)
            if (k != kCapPaper && possible[k]) {'''
b='''        std::array<int,K> candidate_index;candidate_index.fill(-1);
        int candidate_count = 0;
        for (int k = 0; k < K; k++)
            if (k != kCapPaper && possible[k]) {
                candidate_index[k]=candidate_count;'''
assert s.count(a)==1;s=s.replace(a,b)
a='''        std::array<int, K> owner_stamp{};
        int trial_stamp = 0;
        std::array<u64, K> owned;'''
b='''        alignas(32) std::array<int, K+4> owner_stamp{};
        int trial_stamp = 0;
        alignas(32) std::array<u64, K+4> owned{};'''
assert s.count(a)==1;s=s.replace(a,b)
a='''                        owned[k] = one;
                        if (one) owner_stamp[k] = trial_stamp;'''
b='''                        const int ci=candidate_index[k];
                        if(ci>=0) {owned[ci]=one;if(one)owner_stamp[ci]=trial_stamp;}'''
assert s.count(a)==1;s=s.replace(a,b)
a='''                    const __m128i index=_mm_load_si128((const __m128i*)(candidates.data()+cb));
                    const __m128i stamps=_mm_i32gather_epi32(owner_stamp.data(),index,4);
                    const __m256i live=_mm256_cvtepi32_epi64(_mm_cmpeq_epi32(stamps,_mm_set1_epi32(trial_stamp)));
                    const __m256i own=_mm256_mask_i32gather_epi64(_mm256_setzero_si256(),(const long long*)owned.data(),index,live,8);'''
b='''                    const __m128i stamps=_mm_load_si128((const __m128i*)(owner_stamp.data()+cb));
                    const __m256i live=_mm256_cvtepi32_epi64(_mm_cmpeq_epi32(stamps,_mm_set1_epi32(trial_stamp)));
                    const __m256i own=_mm256_and_si256(live,_mm256_load_si256((const __m256i*)(owned.data()+cb)));'''
assert s.count(a)==1;s=s.replace(a,b)
s=s.replace('// integer masks. Masked gathers never read an unstamped owned entry.','// integer masks. Candidate-indexed masks avoid gathers; stale entries are masked out.')
p=root/'solutions/deval-ejectsimd-seq6';p.mkdir();(p/'main.cpp').write_text(s);assert len(s.encode())<=522000
(p/'README.md').write_text('''改良元: `solutions/deval-ejectsimd6`。

必要条件検査の4紙並列化を保ち、ownedとstampを候補番号順の配列に格納する。削除後の表示を走査するときに紙番号から候補番号へ変換して記録し、4紙の検査は連続ロードだけで行う。配列は初期化し、各削除組のstampで古いmaskを無効にする。候補の順序、浮動小数点の計算、ログ・プロファイラと実験スイッチは変えない。
''');print(len(s.encode()))
