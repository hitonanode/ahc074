from pathlib import Path
R=Path(__file__).resolve().parents[2]
s=(R/'solutions/deval-vbranch-o3/main.cpp').read_text()
old='                Q[r] = _mm256_div_ps(numerator, s);'
new='''                // Small nonnegative integer numerators and positive integer
                // denominators. Newton reciprocal plus FMA residual correction
                // agrees with rounded float division over the complete reachable
                // count domain (verified by recip_unit.cpp under GCC and Clang).
                __m256 reciprocal=_mm256_rcp_ps(s);
                reciprocal=_mm256_fmadd_ps(_mm256_fnmadd_ps(reciprocal,s,one),reciprocal,reciprocal);
                const __m256 quotient=_mm256_mul_ps(numerator,reciprocal);
                Q[r]=_mm256_fmadd_ps(_mm256_fnmadd_ps(quotient,s,numerator),reciprocal,quotient);'''
assert old in s;s=s.replace(old,new,1)
d=R/'solutions/deval-recip';d.mkdir(exist_ok=True);(d/'main.cpp').write_text(s)
(d/'README.md').write_text('''# deval-recip

改良元: solutions/deval-vbranch-o3。

焼きなましの穴費用のfloat除算を逆数近似・Newton補正・FMA残差補正に置き換える。入力は小さな非負整数で、到達可能な全ての穴数とresetの組合せについて元の除算とのビット一致をGCCとClangで確認する。fast-mathは使わない。探索予算・乱数・時間ガードは同じ。
''')
