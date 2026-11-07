from pathlib import Path
P=Path(__file__).resolve().parent;root=P.parents[1]
s=(root/'solutions/deval-trim6b/main.cpp').read_text()
a='''    template <class Evaluate>
    void eject_repairs('''
assert s.count(a)==1
s=s.replace(a,'''    template <class Evaluate>
    __attribute__((target("avx2"))) void eject_repairs(''')
a='''        std::array<int, K> candidates;
        int candidate_count = 0;
        for (int k = 0; k < K; k++)
            if (k != kCapPaper && possible[k]) candidates[candidate_count++] = k;'''
b='''        alignas(32) std::array<int, K+4> candidates{};
        alignas(32) std::array<u64, K+4> candidate_opq{}, candidate_wrong{};
        int candidate_count = 0;
        for (int k = 0; k < K; k++)
            if (k != kCapPaper && possible[k]) {
                candidates[candidate_count]=k;
                candidate_opq[candidate_count]=paper[k].opaque;
                candidate_wrong[candidate_count]=paper[k].opaque & (paper[k].black ^ A[u]);
                ++candidate_count;
            }'''
assert s.count(a)==1;s=s.replace(a,b)
a='''                for (int ci = 0; ci < candidate_count; ci++) {
                    const int k = candidates[ci];
                    // The display with k lifted out (its own windows show the paper below) and the
                    // windows then wrong; k must cover them all with the right colors.
                    const u64 own = owner_stamp[k] == trial_stamp ? owned[k] : 0;
                    u64 after = shown ^ ((shown ^ second_black) & own), bad = after ^ A[u];
                    u64 wrong = paper[k].opaque & (paper[k].black ^ A[u]);
                    if (!bad || (bad & ~paper[k].opaque) || (bad & wrong)) continue;'''
b='''                // The four independent necessary-condition tests use the same exact
                // integer masks. Masked gathers never read an unstamped owned entry.
                // Surviving papers are still visited in the original ascending order.
                for(int cb=0;cb<candidate_count;cb+=4) {
                    const __m128i index=_mm_load_si128((const __m128i*)(candidates.data()+cb));
                    const __m128i stamps=_mm_i32gather_epi32(owner_stamp.data(),index,4);
                    const __m256i live=_mm256_cvtepi32_epi64(_mm_cmpeq_epi32(stamps,_mm_set1_epi32(trial_stamp)));
                    const __m256i own=_mm256_mask_i32gather_epi64(_mm256_setzero_si256(),(const long long*)owned.data(),index,live,8);
                    const __m256i bad4=_mm256_xor_si256(_mm256_set1_epi64x(shown ^ A[u]),
                        _mm256_and_si256(_mm256_set1_epi64x(shown ^ second_black),own));
                    const __m256i wrong4=_mm256_load_si256((const __m256i*)(candidate_wrong.data()+cb));
                    const __m256i opq4=_mm256_load_si256((const __m256i*)(candidate_opq.data()+cb));
                    const __m256i failed=_mm256_or_si256(_mm256_andnot_si256(opq4,bad4),_mm256_and_si256(wrong4,bad4));
                    const __m256i valid=_mm256_andnot_si256(_mm256_cmpeq_epi64(bad4,_mm256_setzero_si256()),
                        _mm256_cmpeq_epi64(failed,_mm256_setzero_si256()));
                    unsigned ready=_mm256_movemask_pd(_mm256_castsi256_pd(valid)) & ((1U<<std::min(4,candidate_count-cb))-1);
                    alignas(32) u64 bad_lanes[4];_mm256_store_si256((__m256i*)bad_lanes,bad4);
                    while(ready) {
                    const int lane=__builtin_ctz(ready),ci=cb+lane;ready&=ready-1;
                    const int k=candidates[ci];
                    const u64 bad=bad_lanes[lane],wrong=candidate_wrong[ci];'''
assert s.count(a)==1;s=s.replace(a,b)
a='''                }
            }
    }

    // ==== Post-processing: two deletions and two repairs (neutral rewrite) ===='''
b='''                    }
                }
            }
    }

    // ==== Post-processing: two deletions and two repairs (neutral rewrite) ===='''
assert s.count(a)==1;s=s.replace(a,b)
p=root/'solutions/deval-ejectsimd6';p.mkdir();(p/'main.cpp').write_text(s);assert len(s.encode())<=522000
(p/'README.md').write_text('''改良元: `solutions/deval-trim6b`。

2削除1修復（および同じ列挙を使う1削除1修復）の修復紙に対する必要条件検査をAVX2で4紙同時に行う。各紙のopaqueと注文に対するwrongは列挙の前に保存し、削除の組ごとのownedはstampが一致するレーンだけmasked gatherで読む。通過した紙は元の番号順で処理し、候補・受理順と浮動小数点計算は変えない。既存のプロファイラでejectのexclusive時間が大きかったため、この検査を対象にする。全実験スイッチ、注釈、統計を保つ。時計で探索を切り替えない。
''')
print(len(s.encode()))
