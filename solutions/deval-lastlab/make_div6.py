from pathlib import Path
P=Path(__file__).resolve().parent;root=P.parents[1]
s=(root/'solutions/deval-trim6b/main.cpp').read_text()
for name,table in [('deval-divcorrect6',False),('deval-divtable6',True)]:
 x=s
 if table:
  x=x.replace('struct Design {','''// Exact reciprocal seeds for the integer denominators of the hole model.
inline constexpr auto kHoleReciprocal=[] {
    std::array<float,769> a{};for(int i=1;i<=768;++i)a[i]=1.f/i;return a;
}();
struct Design {''',1)
  calc='const auto reciprocal=_mm256_i32gather_ps(kHoleReciprocal.data(),_mm256_cvttps_epi32(s),4);'
 else:
  calc='''const auto seed=_mm256_rcp_ps(s);
                const auto reciprocal=_mm256_fmadd_ps(seed,_mm256_fnmadd_ps(s,seed,one),seed);'''
 x=x.replace('                Q[r] = _mm256_div_ps(numerator, s);','''                // Counts and reset rates are integers: numerator <=49152,
                // denominator 1..768. Correct the rounded quotient by its FMA residual.
                '''+calc+'''
                const auto quotient=_mm256_mul_ps(numerator,reciprocal);
                Q[r]=_mm256_fmadd_ps(reciprocal,_mm256_fnmadd_ps(quotient,s,numerator),quotient);''')
 assert x!=s and len(x.encode())<=522000
 p=root/'solutions'/name;p.mkdir();(p/'main.cpp').write_text(x)
 (p/'README.md').write_text('改良元: `solutions/deval-trim6b`。\n\n焼きなましの穴費用のSIMD除算を、'+('標準float除算で定めた逆数表' if table else '逆数近似とNewton補正')+'からの商とFMA残差の補正に置き換える実験。穴数の和は256以下、resetは2×目標数なので、分子は49152以下の整数、分母は1–768の整数になる。分子0–65536・分母1–768の照合と、GCC/Clangの解法stdout照合で確認する。fast-mathは使わない。通常250件のcompareで時間を測り、速い場合だけ採用する。\n')
 print(name,len(x.encode()))
