from pathlib import Path
R=Path(__file__).resolve().parents[2]
s=(R/'solutions/dcomp-t11-hash4/main.cpp').read_text()
a='        bool memo = get("MEMO", 1);'
assert s.count(a)==1
s=s.replace(a,a+'\n        bool late_memo = get("LATE_MEMO", 1);')
a='                if (cfg.memo) {\n                    // Only final-order properties are cached.'
assert s.count(a)==1
s=s.replace(a,a.replace('if (cfg.memo)','if (cfg.memo && !cfg.late_memo)'))
a='''            CF_SCOPE(eval_value);
            // as restore(seed) with the order replaced'''
assert s.count(a)==1
s=s.replace(a,'''            CF_SCOPE(eval_value);
            // Legality is path-dependent, but canonicalization and terminal cost
            // depend only on the completed order and this call's fixed seed.
            // Delay hashing until legality passed, so illegal trials neither pay
            // for the hash nor evict a useful entry. Compare all K bytes on hits.
            if(cfg.memo && cfg.late_memo) {
                u64 h0=0xcbf29ce484222325ULL,h1=h0,h2=h0,h3=h0;
                for(int j=0;j<K;j+=32) {
                    u64 w[4];std::memcpy(w,ord.data()+j,32);
                    h0=(h0^w[0])*0x100000001b3ULL;h1=(h1^w[1])*0x100000001b3ULL;
                    h2=(h2^w[2])*0x100000001b3ULL;h3=(h3^w[3])*0x100000001b3ULL;
                }
                const u64 hash=h0^(h1<<13|h1>>51)^(h2<<27|h2>>37)^(h3<<43|h3>>21);
                memo=&end_memo[(hash^(hash>>32))&(end_memo.size()-1)];
                memo_hit=memo->generation==generation && std::memcmp(memo->next.data(),ord.data(),K)==0;
                if(memo_hit) {
                    f2_memo_hits++;
                    if(!memo->reachable)return false;
                } else {
                    f2_memo_misses++;memo->generation=0;
                    std::memcpy(memo->next.data(),ord.data(),K);
                    memo->next[K]=0;
                }
            }
            // as restore(seed) with the order replaced''')
for name,source,check in [('dcomp-t11-latememo',s,False),('dcomp-t11-latememo-check',s,True)]:
    if check:
        a='''                value = path.size() + memo->charge + memo->next_cost;
            } else {'''
        assert source.count(a)==1
        source=source.replace(a,'''                value = path.size() + memo->charge + memo->next_cost;
                top_d=seed.top_d;fillers=seed.fillers;canonicalize();
                const double ref=plan_cost(path.size());
                bool same=fillers.size()==memo->fillers.size();
                for(size_t i=0;same && i<fillers.size();++i) {
                    const auto& a=fillers[i];const auto& b=memo->fillers[i];
                    same=a.paper==b.paper && a.lvl==b.lvl && a.hi==b.hi;
                }
                if(!same || top_d!=memo->top_d || std::memcmp(&ref,&value,sizeof(double)))std::abort();
            } else {''')
    d=R/'solutions'/name;assert not d.exists();d.mkdir();(d/'main.cpp').write_text(source)
    (d/'README.md').write_text('改良元: solutions/dcomp-t11-hash4\n\nend-memoの検索を合法性の再生の後へ移す。不合法な試行ではhashを計算せず、有用なcache entryも追い出さない。世代はpost呼出し単位、keyは完成stackの全192byteで照合する。canonicalizeの元のfiller順は同じ呼出しのseedで固定される。費用の浮動小数点加算順は元と同じ。MEMOとLATE_MEMOスイッチで元の経路も残す。\n\n'+('検証版はhitごとに旧canonicalizeとplan_costを再計算し、filler全属性・top_d・double全bitを照合する。\n\n'if check else '')+'固定予算、時計分岐なし。ログ・trace・profiler・実験スイッチ・目次と段・DesignStoreを保持する。\n')
