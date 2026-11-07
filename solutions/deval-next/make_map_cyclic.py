from pathlib import Path
r=Path(__file__).resolve().parents[2];s=(r/'solutions/deval-seven-wide/main.cpp').read_text()
needle='''            const __m256i noboth = _mm256_cmpeq_epi32(_mm256_and_si256(r, _mm256_srli_epi32(r, 16)), zero);'''
new=needle+'''
            // A block of eight opposite-arc cycles is known incompatible.
            // No witness, old cost, or pending-list work can change these zeros.
            if(_mm256_testz_si256(noboth,noboth)) {
                _mm256_storeu_si256((__m256i*)(ndir+p),r);
                _mm256_storeu_si256((__m256i*)(nrel+p),zero);
                continue;
            }'''
assert needle in s;s=s.replace(needle,new,1)
p=r/'solutions/deval-map-cyclic';p.mkdir(exist_ok=True);(p/'main.cpp').write_text(s);(p/'README.md').write_text('改良元: `solutions/deval-seven-wide`\n\n窓割り当ての関係評価で、8組全てが長さ2の閉路を含む場合は、関係だけ保存して費用をゼロにする。互換性がないことが確定しているため、古い関係・費用・三角閉路の証拠の参照とpendingの仮書込みを省く。固定予算と出力は同じ。\n')
