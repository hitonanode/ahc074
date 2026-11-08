from pathlib import Path
R=Path(__file__).resolve().parents[2];B=(R/'solutions/dcomp-combo-alt1/main.cpp').read_text()
pending='''            _mm256_storeu_si256(
                (__m256i*)(pending + npending),
                _mm256_add_epi32(_mm256_set1_epi32(p), _mm256_loadu_si256((const __m256i*)lanes[need].data())));
            npending += __builtin_popcount(need);'''
valid='''        _mm256_storeu_si256(
            (__m256i*)(valid + nvalid),
            _mm256_add_epi32(_mm256_set1_epi32(p), _mm256_loadu_si256((const __m256i*)lanes[good].data())));
        nvalid += __builtin_popcount(good);'''
assert B.count(pending)==B.count(valid)==1
for name,pend,val in [
 ('skipzeros','            if(need) {\n'+pending+'\n            }','        if(good) {\n'+valid+'\n        }'),
 ('smallbits','            for(unsigned bits=need;bits;bits&=bits-1)pending[npending++]=p+__builtin_ctz(bits);','        for(unsigned bits=good;bits;bits&=bits-1)valid[nvalid++]=p+__builtin_ctz(bits);')]:
 s=B.replace(pending,pend).replace(valid,val)
 d=R/'solutions'/('dcomp-t11-'+name);assert not d.exists();d.mkdir();(d/'main.cpp').write_text(s)
 desc='0 laneの圧縮storeを飛ばす。' if name=='skipzeros' else '8 laneのmaskを下位bit順に列挙し、有効な要素だけをstoreする。'
 (d/'README.md').write_text('改良元: solutions/dcomp-combo-alt1\n\n窓のevaluate_moveでpending（およびClangのvalid）の'+desc+'実要素の昇順・関係費用・目撃cycleの更新順を保つ。従来の0 maskのstoreは実要素の末尾以降だけを書き、その領域は読まれない。\n\nprofileではGCCのev_simdが窓の約24%、validが約10%。固定予算・GCC/Clangの既存選択・ログ・profiler・実験スイッチ・目次と段・DesignStoreを保持する。\n')
