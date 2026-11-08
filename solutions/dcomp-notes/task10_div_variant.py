from pathlib import Path
r=Path(__file__).resolve().parents[2];s=(r/'solutions/dcomp-combo-ten/main.cpp').read_text()
a='                Q[r] = _mm256_div_ps(numerator, s);'
b='''                // Integer counts lie in [0,256], so numerator is an exact half-integer.
                // Refine the reciprocal, then correct the quotient by its exact FMA residual.
                // Exhaustive 257^3 triples give the same bits as DIVPS on GCC and Clang.
                const __m256 inv0=_mm256_rcp_ps(s);
                const __m256 inv=_mm256_fmadd_ps(inv0,_mm256_fnmadd_ps(s,inv0,one),inv0);
                const __m256 quotient=_mm256_mul_ps(numerator,inv);
                Q[r]=_mm256_fmadd_ps(_mm256_fnmadd_ps(quotient,s,numerator),inv,quotient);'''
assert s.count(a)==1;s=s.replace(a,b)
p=r/'solutions/dcomp-div-correct';assert not p.exists();p.mkdir();(p/'main.cpp').write_text(s)
(p/'README.md').write_text('''改良元: solutions/dcomp-combo-ten

焼きなましのSIMD handle費用の除算を、逆数のNewton補正と商のFMA残差補正で計算する。N0/N1/resetは0〜256の整数なので分子は正確な半整数であり、この範囲の全257^3=16,974,593組を独立の数値検査でGCC/Clangとも元のDIVPSとbit一致と確認した。fast-mathは使わず、加算順と採否は維持する。実際のsolverでも出力同一と時間を測る。scalar qfは変更しない。予算・実験スイッチ・ログ・DesignStoreは元のまま。時間fallbackなし。
''')
