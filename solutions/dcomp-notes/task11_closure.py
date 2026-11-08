from pathlib import Path
R=Path(__file__).resolve().parents[2];B=(R/'solutions/dcomp-combo-alt1/main.cpp').read_text()
def rep(s,a,b,n=1):assert s.count(a)==n,(s.count(a),a[:90]);return s.replace(a,b)
s=B
s=rep(s,'    std::vector<uint32_t> wit;\n    std::vector<int> u, v;',
'''    std::vector<uint32_t> wit;
    struct Equiv { uint32_t raw=~0U,allowed=0,required=0;u64 closed=0; };
    std::vector<Equiv> equiv;
    std::vector<unsigned> reuse_epoch;
    std::vector<int> reused;
    unsigned reuse_serial=0;
    long long closure_reused=0,closure_equiv_built=0;
    std::vector<int> u, v;''')
s=rep(s,'        words = (n8 + 63) / 64;',
'''        words = (n8 + 63) / 64;
        equiv.resize(n8);reuse_epoch.assign(n8,0);reused.reserve(n8);''')
x='''    // the closures first, without a branch on their cycles (pending[] is compacted to the'''
code=r'''    // For a DAG, every graph containing its transitive reduction and contained
    // in its closure has exactly that closure. Test only pending old-valid pairs.
    // The reduction and closure are cached by the complete old raw relation.
    if(++P.reuse_serial==0){std::fill(P.reuse_epoch.begin(),P.reuse_epoch.end(),0);P.reuse_serial=1;}
    P.reused.clear();
    int unresolved=0;
    for(int i=0;i<npending;++i) {
        const int p=pending[i];bool same=false;
        if(prel[p]) {
            auto& memo=P.equiv[p];
            if(memo.raw!=pdir[p]) {
                ++P.closure_equiv_built;
                const u64 c=relations.closure(pdir[p]);
                u64 indirect=0;
                for(int j=0;j<6;++j)
                    indirect|=((c>>j)&0x0101010101010101ULL)*((c>>(8*j))&255);
                const u64 reduced=c&~indirect;
                uint32_t reverse,forward;
                implied_arcs(c,reverse,forward);const uint32_t allowed=forward|(reverse<<16);
                implied_arcs(reduced,reverse,forward);const uint32_t required=forward|(reverse<<16);
                memo={pdir[p],allowed,required,c};
            }
            const uint32_t r=ndir[p];
            same=(r&memo.required)==memo.required && !(r&~memo.allowed);
#ifdef CLOSURE_EQUIV_CHECK
            if(same && relations.closure(r)!=memo.closed) {
                std::cerr<<"CLOSURE_EQUIV_MISMATCH "<<p<<'\n';std::abort();
            }
#endif
        }
        if(same){P.reuse_epoch[p]=P.reuse_serial;P.reused.push_back(p);++P.closure_reused;}
        else pending[unresolved++]=p;
    }
    npending=unresolved;
'''
s=rep(s,x,code+x)
s=rep(s,'    for(int p:P.live)nrel[p]=prel[p]*int(ndir[p]==pdir[p]);',
'''    for(int p:P.live)nrel[p]=prel[p]*int(ndir[p]==pdir[p] || P.reuse_epoch[p]==P.reuse_serial);''')
s=rep(s,'    for (int k = 0; k < nacyclic; ++k) nrel[pending[k]] = 1 + relations.sums.both_of(closures[k]);',
'''#if defined(__clang__)
    for(int p:P.reused)nrel[p]=prel[p];
#endif
    for (int k = 0; k < nacyclic; ++k) nrel[pending[k]] = 1 + relations.sums.both_of(closures[k]);''')
s=rep(s,'    for(int p:P.live)live_bits[p>>6]|=u64(ndir[p]==pdir[p])<<(p&63);',
'''    for(int p:P.live)live_bits[p>>6]|=u64(ndir[p]==pdir[p] || P.reuse_epoch[p]==P.reuse_serial)<<(p&63);''')
x='    std::cerr << "search_accept = " << accepted'
assert s.count(x)==1
s=s.replace(x,'''    std::cerr<<"closure_reused = "<<pairs.closure_reused<<"\\nclosure_equiv_built = "<<pairs.closure_equiv_built<<'\\n';
'''+x)
for name,src,desc in [('dcomp-t11-closure-eq',s,''),('dcomp-t11-closure-check','#define CLOSURE_EQUIV_CHECK 1\n'+s,'再利用した全関係の閉包を元の関数でも求め、64bit行列が一致することを検査する。')]:
 d=R/'solutions'/name;assert not d.exists();d.mkdir();(d/'main.cpp').write_text(src)
 (d/'README.md').write_text('改良元: solutions/dcomp-combo-alt1\n\n窓割当で、旧互換ペアの変更後の辺集合が「旧DAGの推移的簡約以上、旧閉包以下」なら閉包は同じである。この場合だけ旧費用を再利用する。閉包と簡約は旧raw relation完全一致をkeyとして記憶する。ペアの列挙順・matchingの同点順は保つ。'+desc+'\n\nclosure_reusedは省略数、closure_equiv_builtはcache作成数。両コンパイラの探索予算・既存ログ・profiler・実験スイッチ・目次と段・DesignStoreは保持。時計による切替はない。\n')
