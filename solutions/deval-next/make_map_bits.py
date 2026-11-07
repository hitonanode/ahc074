from pathlib import Path
r=Path(__file__).resolve().parents[2];b=(r/'solutions/deval-seven-wide/main.cpp').read_text()
a='''            const __m256i ar = _mm256_or_si256(
                _mm256_load_si256((const __m256i*)directions[a_fwd & 255].data()),
                _mm256_slli_epi32(_mm256_load_si256((const __m256i*)directions[a_rev & 255].data()), 16));'''
x='''            const __m256i ar = _mm256_and_si256(
                _mm256_srlv_epi32(_mm256_set1_epi32(int((a_fwd&255)|((a_rev&255)<<16))),
                                  _mm256_setr_epi32(0,1,2,3,4,5,6,7)),_mm256_set1_epi32(0x10001));'''
a2='''                const __m256i br = _mm256_or_si256(
                    _mm256_load_si256((const __m256i*)directions[b_fwd & 255].data()),
                    _mm256_slli_epi32(_mm256_load_si256((const __m256i*)directions[b_rev & 255].data()), 16));'''
x2='''                const __m256i br = _mm256_and_si256(
                    _mm256_srlv_epi32(_mm256_set1_epi32(int((b_fwd&255)|((b_rev&255)<<16))),
                                      _mm256_setr_epi32(0,1,2,3,4,5,6,7)),_mm256_set1_epi32(0x10001));'''
assert a in b and a2 in b;s=b.replace(a,x,1).replace(a2,x2,1)
def put(name,s,desc):
 p=r/'solutions'/name;p.mkdir(exist_ok=True);(p/'main.cpp').write_text(s);(p/'README.md').write_text('改良元: `solutions/deval-seven-wide`\n\n'+desc+'\n\n関係と候補順を同じに保ち、固定予算で評価する。時間による打切りはない。\n');print(name,len(s.encode()))
put('deval-map-bits',s,'窓割り当ての関係評価で、8組の方向ビットを表参照の代わりにAVX2の可変シフトで展開する。整数演算のみ。')
a='''            _mm256_storeu_si256(
                (__m256i*)(pending + npending),
                _mm256_add_epi32(_mm256_set1_epi32(p), _mm256_loadu_si256((const __m256i*)lanes[need].data())));
            npending += __builtin_popcount(need);'''
assert a in s;s=s.replace(a,'            if(need) {\n'+a+'\n            }',1)
put('deval-map-pending',s,'deval-map-bitsに加え、閉包を再計算する組がない8要素ブロックではpendingへの仮書込みを省く。')
