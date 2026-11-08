from pathlib import Path
r=Path(__file__).resolve().parents[2];s=(r/'solutions/dcomp-hole4/main.cpp').read_text()
x='''    std::vector<uint32_t> pair_tail(np);
    for (int p = 0; p < np; p++) pair_tail[p] = uint32_t(p) << 16 | uint32_t(pairs.u[p]) << 8 | uint32_t(pairs.v[p]);
    std::vector<u64> keyed(np), tmp(np), sorted(np);'''
y='''    // Seventeen cost bits and fifteen pair-index bits fit in one 32-bit word.
    // Stable scatters retain the old tie order; fetch the two targets only in greedy.
    static_assert(P*(P-1)/2 < (1<<15));
    std::vector<uint16_t> pair_uv(np);
    for(int p=0;p<np;++p)pair_uv[p]=(unsigned(pairs.u[p])<<8)|unsigned(pairs.v[p]);
    std::vector<uint32_t> keyed(np), tmp(np), sorted(np);'''
assert s.count(x)==1;s=s.replace(x,y)
a=s.index('    auto matching_cost =');b=s.index('    // the pairs (ndir, nrel, valid);',a);t=s[a:b]
for x,y in [('keyed[i] = u64(key) << 32 | pair_tail[p];','keyed[i] = uint32_t(key) << 15 | unsigned(p);'),('(keyed[i] >> 32) & 255','(keyed[i] >> 15) & 255'),('tmp[i] >> 40','tmp[i] >> 23'),('''            const u64 x = sorted[i];
            const unsigned u = unsigned(x >> 8) & 255, v = unsigned(x) & 255;''','''            const uint32_t x=sorted[i];const unsigned p=x&32767;
            const unsigned uv=pair_uv[p],u=uv>>8,v=uv&255;'''),('out[matched] = int(x >> 16) & 0xffff;','out[matched] = p;'),('(long long)(x >> 32)','(long long)(x >> 15)')]:
 assert t.count(x)==1,(x,t.count(x));t=t.replace(x,y)
s=s[:a]+t+s[b:]
p=r/'solutions/dcomp-key32';assert not p.exists();p.mkdir();(p/'main.cpp').write_text(s)
(p/'README.md').write_text('改良元: solutions/dcomp-hole4\n\nmatching_costのradix sortのレコードを64bitから32bitへする。費用17bitとペア番号15bitは32bitに収まり、同点順は元の安定sortと同じ。greedyでだけペア番号から2 targetを16bit表で読む。2回のscatterとkey構築の転送量を半減させる代わりに、greedyで表読み1回が増える。\n\n費用・選択順・乱数・固定予算と要求処理は不変。ログ・profiler・実験スイッチ・DesignStoreを維持、時間fallbackなし。\n')
