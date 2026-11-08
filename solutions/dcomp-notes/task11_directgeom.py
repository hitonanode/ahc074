from pathlib import Path
R=Path(__file__).resolve().parents[2]
s=(R/'solutions/dcomp-combo-alt1/main.cpp').read_text()
a='''                    prepare_positions();
                    // without_pos(w): the position, in the order without k, of the top opaque paper
                    // other than k at window w
                    // A paper beyond the top-two-layer prefix is below every relevant
                    // first owner. K has the same effect on the geometry as its actual rank.
                    int pos = owner_stamp[k]==trial_stamp?ord_position[k]:K;
                    int lo = 0, hi = K - 1;
                    auto without_pos = [&](int w) {
                        int p = first[w] == pos ? second[w] : first[w];
                        return p - int(p > pos);
                    };
                    for (u64 z = bad; z; z &= z - 1) hi = std::min(hi, without_pos(__builtin_ctzll(z)));
                    for (u64 z = wrong; z && lo <= hi; z &= z - 1)
                        lo = std::max(lo, without_pos(__builtin_ctzll(z)) + 1);'''
assert s.count(a)==1
legacy=a[a.index('                    prepare_positions();'):]
body='''                    // Only two extrema of the first-owner positions are needed.
                    // In G without k, hi is the first paper touching any bad window;
                    // lo is one past the last first owner of k's wrong-color windows.
                    // G's top-two-layer prefix contains all such owners after one removal.
                    int pos=owner_stamp[k]==trial_stamp?ord_position[k]:K;
                    int lo=0,hi=K-1;bool found_bad=false;
                    u64 remaining_wrong=wrong;
                    for(int t=0;t<processed;++t) {
                        const int x=ord[t];if(x==k)continue;
                        const int p=t-int(t>pos);const u64 mask=paper[x].opaque;
                        if(!found_bad && (mask&bad)){hi=p;found_bad=true;}
                        if(mask&remaining_wrong){lo=p+1;remaining_wrong&=~mask;}
                        if(found_bad && (lo>hi || !remaining_wrong))break;
                    }
                    if(remaining_wrong && lo<=hi)lo=K; // a missing owner makes every gap illegal
#ifdef DIRECT_GEOMETRY_CHECK
                    prepare_positions();
                    int rl=0,rh=K-1;
                    auto reference_pos=[&](int w){int p=first[w]==pos?second[w]:first[w];return p-int(p>pos);};
                    for(u64 z=bad;z;z&=z-1)rh=std::min(rh,reference_pos(__builtin_ctzll(z)));
                    for(u64 z=wrong;z && rl<=rh;z&=z-1)rl=std::max(rl,reference_pos(__builtin_ctzll(z))+1);
                    if((lo<=hi)!=(rl<=rh) || (lo<=hi && (lo!=rl || hi!=rh))) {
                        std::cerr<<"DIRECT_GEOMETRY_MISMATCH "<<lo<<' '<<hi<<' '<<rl<<' '<<rh<<'\\n';std::abort();
                    }
#endif'''
s=s.replace(a,'#ifdef DIRECT_GEOMETRY_LEGACY\n'+legacy+'\n#else\n'+body+'\n#endif')
# The older full-order geometry checker is retained and checks all usable endpoints.
a='''#ifdef EJECT_GEOM_CHECK
                    prepare_order();''';assert s.count(a)==1;s=s.replace(a,a+'prepare_positions();')
a='if(rl!=lo || rh!=hi){std::cerr<<"EJECT_GEOMETRY_MISMATCH';assert s.count(a)==1
s=s.replace(a,'if((rl<=rh)!=(lo<=hi) || (lo<=hi && (rl!=lo || rh!=hi))){std::cerr<<"EJECT_GEOMETRY_MISMATCH')
for name,source,extra in [('dcomp-t11-direct-geometry',s,''),('dcomp-t11-direct-geometry-check','#define DIRECT_GEOMETRY_CHECK 1\n#define EJECT_GEOM_CHECK 1\n'+s,'検証版は全幾何候補で元のfirst/second表と完全な紙順序から再計算し、合法区間の有無と全ての採用可能端点を照合する。')]:
 d=R/'solutions'/name;assert not d.exists();d.mkdir();(d/'main.cpp').write_text(source)
 (d/'README.md').write_text('改良元: solutions/dcomp-combo-alt1\n\neject修復の挿入区間を、128窓のfirst/second位置表を作らずに直接求める。紙kを抜いた順序を上から見て、bad窓に初めて触れる紙が上端、wrong色窓の全ての最初のownerが揃う最後の紙の次が下端となる。k一枚を除くだけなので、既に構築したtop-two-layer prefixで十分。端点が逆転した候補は元と同じく棄却する。'+extra+'\n\nDIRECT_GEOMETRY_LEGACYで元の表方式も残す。整数の集合演算だけを変え、候補順・予算・浮動小数点計算を保持する。ログ・trace・profiler・実験スイッチ・目次と段・DesignStoreを保持し、時計分岐なし。\n')
