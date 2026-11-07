from pathlib import Path
r=Path(__file__).resolve().parents[2];s=(r/'solutions/deval-seven-wide/main.cpp').read_text()
a='                Q[r] = _mm256_div_ps(numerator, s);'
assert a in s
s=s.replace(a,'''                // Search surrogate: one Newton refinement of the hardware reciprocal.
                // This intentionally changes the annealing trajectory; final V is unchanged.
                const __m256 r0=_mm256_rcp_ps(s);
                const __m256 reciprocal=_mm256_mul_ps(r0,_mm256_fnmadd_ps(s,r0,_mm256_set1_ps(2.f)));
                Q[r] = _mm256_mul_ps(numerator, reciprocal);''',1)
p=r/'solutions/deval-anneal-recip';p.mkdir(exist_ok=True);(p/'main.cpp').write_text(s);(p/'README.md').write_text('改良元: `solutions/deval-seven-wide`\n\n焼きなまし中のハンドル費用の除算をAVX2の近似逆数とNewton補正1回で計算する。目的関数のごく小さい丸め差で軌道が変わるため、出力一致の高速化とは別の探索効率実験として8リストで検証する。完成設計のV、仕上げ、注文処理、反復予算は同じ。fast-mathは使わず、時間で打ち切らない。\n')
