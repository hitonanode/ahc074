"""Diagnostic copies serialize completed candidates, including their raw assignment."""
from pathlib import Path
root=Path(__file__).resolve().parents[2]
needle='        if(env_int("DEVAL_DUMP_FEATURES"))std::cerr<<"@deval_final "<<id<<\' \'<<v<<\'\\n\';'
trace='''
#ifdef LOCAL_BENCH
        // Audit only: exact integers and double bit patterns, without clock
        // fields or changing cerr formatting. Never used by candidate selection.
        {
            std::ostringstream a;
            u64 vb=0,cb=0;std::memcpy(&vb,&v,sizeof(v));std::memcpy(&cb,&des->cur,sizeof(des->cur));
            a<<"@dcomp_candidate "<<id<<' '<<std::hex<<vb<<' '<<cb<<' '<<des->rng.x
             <<' '<<candidate.emergency<<' '<<candidate.M<<' '<<candidate.G<<' '<<candidate.H;
            auto list=[&](const auto& xs){a<<' '<<xs.size();for(const auto& x:xs)a<<' '<<x;};
            list(candidate.A);list(candidate.permutation);list(candidate.polarity);
            list(candidate.columns);list(candidate.ded);list(candidate.handle);
            a<<' '<<candidate.edge.size();for(auto [x,y]:candidate.edge)a<<' '<<x<<' '<<y;
            a<<' '<<candidate.papers.size();for(const auto& x:candidate.papers)a<<' '<<x.opaque<<' '<<x.black;
            a<<' '<<des->unit.size();for(const auto& u:des->unit)a<<' '<<u.a<<' '<<u.b<<' '<<u.c;
            std::cerr<<a.str()<<'\\n';
        }
#endif
'''
for count in ['nine','ten']:
    parent='dcomp-'+count+'-fast';name='dcomp-'+count+'-audit'
    s=(root/'solutions'/parent/'main.cpp').read_text();assert s.count(needle)==1
    p=root/'solutions'/name;p.mkdir(exist_ok=True)
    (p/'main.cpp').write_text(s.replace(needle,needle+trace))
    (p/'README.md').write_text('改良元: solutions/'+parent+'\n\n候補の同一性を検査する診断版。各完成候補についてVとcurのdoubleのbit表現、乱数状態、DesignStateの全ての設計値、raw unit割当を@dcomp_candidate行へLOCAL_BENCHで出す。選択や乱数は変更しない。元の固定予算・注文処理・ログ・実験スイッチを保持し、時間不足の切替は加えない。\n')
