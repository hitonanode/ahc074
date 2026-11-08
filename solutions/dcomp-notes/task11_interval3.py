from pathlib import Path
R=Path(__file__).resolve().parents[2];B=(R/'solutions/dcomp-t11-interval-wide/main.cpp').read_text()
def rep(s,a,b):
 assert s.count(a)==1,(a[:80],s.count(a))
 return s.replace(a,b)
for name,formula,desc in [
 ('opaque','__builtin_popcountll(h_opq[x]&low_bits(cd.c+1)&~low_bits(cd.lvl))','区間内で実際に不透明な取っ手の数'),
 ('cover','std::accumulate(stay_table[x][cd.lvl].cover.begin(),stay_table[x][cd.lvl].cover.begin()+H,0.)','将来の注文の取っ手穴を覆う確率の総和'),
 ('prob','stay_table[x][cd.lvl].probability','次の注文でもfillerがそのまま正しい確率')]:
 s=rep(B,'''        bool post = false;
    };
    // Weighted interval scheduling''','''        bool post = false;
        double tie_credit=0;
    };
    // Weighted interval scheduling''')
 s=rep(s,'std::array<int,65> secondary{};','std::array<double,65> secondary{};')
 s=rep(s,'auto tie_score=[](const Cand& cd){return cd.c-cd.lvl+1;};','auto tie_score=[](const Cand& cd){return cd.tie_credit;};')
 s=rep(s,'''        const auto picks = best_intervals(cand);
        if (opt.value_fillers''','''        if(interval_tie_mode)for(auto& row:cand)for(auto& cd:row) {
            const int x=cd.kind==0?cd.idx:cd.kind==3?x0:olds[cd.idx].paper;
            cd.tie_credit='''+formula+''';
        }
        const auto picks = best_intervals(cand);
        if (opt.value_fillers''')
 d=R/'solutions'/('dcomp-t11-interval-'+name);assert not d.exists();d.mkdir();(d/'main.cpp').write_text(s)
 (d/'README.md').write_text('改良元: solutions/dcomp-t11-interval-wide\n\njoint filler区間DPの一次費用が同じ場合、'+desc+'の和が大きい組を選ぶ。weighted/complete-value計画、候補数、要求予算は変えない。同じ二次値なら後の区間を選ぶ。\n\n両コンパイラ共通設定。時計による切替なし。ログ・trace・profiler・実験スイッチ・目次と段・DesignStoreを保持する。\n')
