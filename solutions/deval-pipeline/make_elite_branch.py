from pathlib import Path
P=Path(__file__).resolve().parent;R=P.parents[1]
b=(R/'solutions/deval-elite-probe/main.cpp').read_text()
a=b.index('    int min_broken=1000,zero_broken=0;');z=b.index('    std::unique_ptr<Design> best_assignment;',a)
b=b[:a]+'''    const Comparator base_comp=comp;
    std::unique_ptr<Design> alternate;
    Comparator alternate_comp=comp;
    int elite_used=0,elite_broken=0;
    const double elite_begin=elapsed_sec();
    std::vector<std::pair<int,int>> eligible_elites;
    for(int i=0;i<int(window_elite_snapshots.size());++i) {
        const auto& e=window_elite_snapshots[i];
        Comparator c=comp;c.edge=e.edges;c.polarity=e.polarity;c.rebuild();
        int broken=0;for(const auto& u:prefix->unit)if(u.b>=0)broken+=!c.compatible(prefix->A[u.a],prefix->A[u.b]);
        eligible_elites.push_back({broken,i});
    }
    ELITE_ORDER
    for(const auto& [broken,at]:eligible_elites) {
        const auto& e=window_elite_snapshots[at];
        Comparator c=base_comp;c.edge=e.edges;c.polarity=e.polarity;c.rebuild();
        auto d=std::make_unique<Design>(*prefix);
        for(auto& v:d->partners)v.clear();
        for(auto& v:d->ok)v.fill(0);
        for(auto& v:d->gcost)v.fill(0);
        for(int a=0;a<P;++a)for(int b=a+1;b<P;++b)if(c.compatible(d->A[a],d->A[b])) {
            d->ok[a][b]=d->ok[b][a]=1;d->partners[a].push_back(b);d->partners[b].push_back(a);
            const auto reach=c.closure(d->A[a],d->A[a]^d->A[b]);u64 r=0;
            for(int j=0;j<M;++j)r|=u64(reach[j])<<(8*j);
            d->gcost[a][b]=d->gcost[b][a]=PosetSums::get().both_of(r)/1440.0;
        }
        d->rebuild();bool valid=true;
        // Repair incompatible pairs by exchanging one target with a single.
        // Keeping each slot's handle color preserves feasibility of all columns.
        for(int x=0;x<d->U&&valid;++x) {
            const auto ox=d->unit[x];if(ox.b<0||d->ok[ox.a][ox.b])continue;
            double best=1e100;int by=-1;Design::Unit bx{},bs{};
            for(int y=0;y<d->U;++y)if(d->unit[y].b<0)for(int f=0;f<2;++f) {
                const auto oy=d->unit[y];const int a=f?ox.b:ox.a,b=f?ox.a:ox.b;
                Design::Unit nx{a,oy.a,ox.c},ny{b,-1,oy.c};
                if(!d->ok[a][oy.a]||!d->valid(nx,nx.c)||d->color(ny,ny.c)!=d->color(oy,oy.c))continue;
                const double old=d->cur;
                d->update(ox,-1);d->update(oy,-1);d->update(nx,1);d->update(ny,1);
                if(d->cur<best){best=d->cur;by=y;bx=nx;bs=ny;}
                d->update(nx,-1);d->update(ny,-1);d->update(ox,1);d->update(oy,1);d->cur=old;
            }
            if(by<0){valid=false;break;}
            d->unit[x]=bx;d->unit[by]=bs;d->rebuild();
        }
        if(valid){alternate=std::move(d);alternate_comp=std::move(c);elite_used=1;elite_broken=broken;}
        break; // Fixed single alternative: do not spend more on difficult cases.
    }
    std::cerr<<"elite_used = "<<elite_used<<"\\nelite_broken = "<<elite_broken
             <<"\\nelite_prepare_sec = "<<elapsed_sec()-elite_begin<<'\\n';
''' +b[z:]
b=b.replace('''        des=std::make_unique<Design>(*prefix);
        if(i)''','''        comp=(i==3&&alternate)?alternate_comp:base_comp;
        des=std::make_unique<Design>(i==3&&alternate?*alternate:*prefix);
        if(i)''',1)
b=b.replace('''        des=std::make_unique<Design>(*best_assignment);
        des->rng''','''        comp.edge=state.edge;comp.polarity=state.polarity;comp.rebuild();
        des=std::make_unique<Design>(*best_assignment);
        des->rng''',1)
for name,order in [('deval-elite-branch',''),('deval-elite-close','std::sort(eligible_elites.begin(),eligible_elites.end());')]:
 s=b.replace('ELITE_ORDER',order)
 s=s.replace('// Empty for ordinary finishing. The final design-only search can accept a\n// complete Hungarian cycle using V instead of its linear proposal model.\n','').replace('// A proposal exchanges complete single/pair target units between physical slots.\n','')
 # Remove blank comment-only lines in this experimental block if source needs room later.
 p=R/'solutions'/name;p.mkdir();(p/'main.cpp').write_text(s)
 (p/'README.md').write_text('改良元: `solutions/deval-ordered8`（診断用deval-elite-probeの保存処理を使用）。\n\n窓割当てelite poolのうち同じ汎用窓集合を持つ別割当てを、4本目の枝に使う。共有前半の状態を引き継ぎ、不整合のペアは単独紙との1ターゲット交換で修復する。各スロットの色を保ち、元の仕上げ目的で修復先を選ぶ。'+('窓目的が最小の別割当てを使う。' if not order else '壊れるペアが最少の別割当てを使う。')+'代替がない・修復不能の場合も4枝の探索回数は同じ。完成設計をVで選び、再仕上げには選ばれた窓割当てを引き継ぐ。時間による打切り・予算変更はない。\n\nelite_used / elite_broken / elite_prepare_secは別割当ての採用可否・修復ペア数・準備時間。\n')
 print(name,len(s.encode()))
