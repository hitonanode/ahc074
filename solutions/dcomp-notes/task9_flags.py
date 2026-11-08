"""Construct AVX2 direction flags from packed bytes instead of table loads."""
from pathlib import Path
root=Path(__file__).resolve().parents[2]
s=(root/'solutions/dcomp-nine/main.cpp').read_text()
for prefix in ['a','b']:
    indent='            ' if prefix=='a' else '                '
    a=f'''{indent}const __m256i {prefix}r = _mm256_or_si256(
{indent}    _mm256_load_si256((const __m256i*)directions[{prefix}_fwd & 255].data()),
{indent}    _mm256_slli_epi32(_mm256_load_si256((const __m256i*)directions[{prefix}_rev & 255].data()), 16));'''
    b=f'''{indent}// Lane l receives forward bit l and reverse bit l at bit 16.
{indent}const __m256i {prefix}r=_mm256_and_si256(
{indent}    _mm256_srlv_epi32(_mm256_set1_epi32(int(({prefix}_fwd&255)|(({prefix}_rev&255)<<16))),
{indent}        _mm256_setr_epi32(0,1,2,3,4,5,6,7)),_mm256_set1_epi32(0x10001));'''
    assert s.count(a)==1,(prefix,s.count(a))
    s=s.replace(a,b)
p=root/'solutions/dcomp-nine-arcflags';p.mkdir(exist_ok=True)
(p/'main.cpp').write_text(s)
(p/'README.md').write_text('''改良元: solutions/dcomp-nine

窓探索のSIMD relation更新で、forward/reverseの8bitフラグを直接broadcastし、laneごとの可変右シフトとmaskで有向辺へ展開する。256要素の方向表からのランダムロードを省く。各laneのbit0/16は元の表引きと厳密に同じで、辺方向のshiftと後続処理は不変。

探索回数、乱数列、9候補、浮動小数点演算、注文処理、CLOCK_SCALE、ログ、実験スイッチとプロファイラを保つ。時間不足の切替なし。
''')
