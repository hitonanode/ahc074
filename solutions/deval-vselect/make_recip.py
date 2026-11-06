"""Test a Newton-refined reciprocal in the annealer's SIMD hole update."""
from pathlib import Path
HERE=Path(__file__).resolve().parent
DEST=HERE.parent/'deval-vrecip'
src=(HERE.parent/'deval-vreheat/main.cpp').read_text()
src=src.replace('env_real("DEVAL_REHEAT",4.)','env_real("DEVAL_REHEAT",2.)')
needle='            return (a * b + .5f * reset * std::min(a, b)) / (s > 1.f ? s : 1.f);'
assert needle in src
src=src.replace(needle,'''            const __m128 den=_mm_set_ss(s>1.f?s:1.f);
            __m128 inv=_mm_rcp_ss(den);
            inv=_mm_fmadd_ss(inv,_mm_fnmadd_ss(den,inv,_mm_set_ss(1.f)),inv);
            return (a*b+.5f*reset*std::min(a,b))*_mm_cvtss_f32(inv);''')
needle='                Q[r] = _mm256_div_ps(numerator, s);'
assert needle in src
src=src.replace(needle,'''                // One Newton step leaves only float rounding error. Use the
                // same reciprocal in scalar qf so unchanged lanes remain zero.
                __m256 inv=_mm256_rcp_ps(s);
                inv=_mm256_fmadd_ps(inv,_mm256_fnmadd_ps(s,inv,one),inv);
                Q[r]=_mm256_mul_ps(numerator,inv);''')
assert len(src.encode())<520000
DEST.mkdir(exist_ok=True);(DEST/'main.cpp').write_text(src)
(DEST/'README.md').write_text('''# deval-vrecip

改良元: `solutions/deval-vreheat`。

焼きなましの handle 費用で、AVX2 の除算を逆数近似と Newton 法 1 回に変える。スカラー初期化も同じ逆数で計算し、変更のない要素の差をゼロに保つ。float の丸めが変わるので探索経路は変わる。分岐の温度倍率は 2。その他の候補作成・V16・保存形式・時間ガードは親と同じ。

再生成: `solutions/deval-vselect/make_recip.py`。実測で速度と新しい注文列のスコアを確認して採否を決める。
''')
print('source bytes',len(src.encode()))
