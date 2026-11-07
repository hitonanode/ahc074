from pathlib import Path
P=Path(__file__).resolve().parent;R=P.parents[1]
b=(R/'solutions/deval-ordered8/main.cpp').read_text()
for name,heads,draws in [('deval-vheads',True,False),('deval-vdraw',False,True),('deval-vfast',True,True)]:
 s=b
 if heads:
  old='''        for(auto& a:head)a={-1,-1};
        for(int t=0;t<P;++t) {'''
  new='''        for(auto& a:head)a={-1,-1};
        // A lower-frequency paper can never become a representative. Its
        // geometry and utility are not read by any cover expectation.
        std::array<std::array<int,2>,MaxH> maxfreq{};
        for(int k=0;k<K;++k)if(s.col[k]>=0) {
            auto& f=maxfreq[s.col[k]][s.bl[k]>>s.col[k]&1];f=std::max(f,int(s.freq[k]));
        }
        for(int t=0;t<P;++t) {'''
  assert old in s;s=s.replace(old,new,1)
  old='''                if(c<0||c==s.col[own])continue;
                const U64 shown=s.op[k]&~s.op[own];'''
  new='''                if(c<0||c==s.col[own]||s.freq[k]!=maxfreq[c][s.bl[k]>>c&1])continue;
                const U64 shown=s.op[k]&~s.op[own];'''
  assert old in s;s=s.replace(old,new,1)
 if draws:
  s=s.replace('__attribute__((target("popcnt"))) inline CoverResult expectation','__attribute__((target("popcnt,avx2"))) inline CoverResult expectation',1)
  old='''            for(int c=0;c<s.H;++c)
                colors|=U64((draws[sample][c]^shifts[t][c])<threshold[c])<<c;'''
  new='''            int c=0;
            for(;c+8<=s.H;c+=8) {
                const auto x=_mm256_xor_si256(
                    _mm256_loadu_si256(reinterpret_cast<const __m256i*>(draws[sample].data()+c)),
                    _mm256_loadu_si256(reinterpret_cast<const __m256i*>(shifts[t].data()+c)));
                const auto y=_mm256_loadu_si256(reinterpret_cast<const __m256i*>(threshold.data()+c));
                colors|=U64(_mm256_movemask_ps(_mm256_castsi256_ps(_mm256_cmpgt_epi32(y,x))))<<c;
            }
            for(;c<s.H;++c)colors|=U64((draws[sample][c]^shifts[t][c])<threshold[c])<<c;'''
  assert old in s;s=s.replace(old,new,1)
 p=R/'solutions'/name;p.mkdir(exist_ok=True);(p/'main.cpp').write_text(s)
 (p/'README.md').write_text('改良元: `solutions/deval-ordered8`。\n\nVの出力を保つ高速化。'+('各列・色の最大担当数に満たない紙は代表紙になれないため、未使用のfiller形状・価値計算を省く。' if heads else '')+('固定積分点からの色マスク生成をAVX2の整数比較で8窓ずつ行う。' if draws else '')+'代表紙と積分点、浮動小数点の集計順、探索予算を保つ。時計による切り替えなし。\n')
 print(name,len(s.encode()))
