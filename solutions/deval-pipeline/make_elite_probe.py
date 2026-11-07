from pathlib import Path
P=Path(__file__).resolve().parent;R=P.parents[1]
s=(R/'solutions/deval-ordered8/main.cpp').read_text()
s=s.replace('struct WindowStats {','''struct WindowEliteSnapshot {
    std::vector<std::pair<int,int>> edges;
    std::vector<int> polarity;
    double cost;
};
std::vector<WindowEliteSnapshot> window_elite_snapshots;
struct WindowStats {''',1)
needle='''    stats.gobj_after = cur;
    for (int j = 0; j < g; j++) {'''
insert='''    stats.gobj_after = cur;
    window_elite_snapshots.clear();
    u64 final_generic=0;for(u64 x:mask)final_generic|=x;
    int same_set=0,total_elite=0;
    for(const auto& e:elites)if(e.ready) {
        ++total_elite;
        if(e.generic!=final_generic)continue;
        ++same_set;
        WindowEliteSnapshot x;x.cost=e.cost;
        bool different=false;
        for(int j=0;j<g;++j) {
            const int w=order[j];
            x.edges.push_back(ep[e.which[w]]);x.polarity.push_back(e.pol>>w&1);
            different|=!(mask[e.which[w]]>>w&1)||((e.pol^pol)>>w&1);
        }
        if(different)window_elite_snapshots.push_back(std::move(x));
    }
    std::sort(window_elite_snapshots.begin(),window_elite_snapshots.end(),[](const auto& a,const auto& b){return a.cost<b.cost;});
    std::cerr<<"elite_total = "<<total_elite<<"\\nelite_same_set = "<<same_set
             <<"\\nelite_alternates = "<<window_elite_snapshots.size()<<'\\n';
    for (int j = 0; j < g; j++) {'''
assert needle in s;s=s.replace(needle,insert,1)
needle='''    const auto prefix=std::make_unique<Design>(*des);
    std::unique_ptr<Design> best_assignment;'''
insert='''    const auto prefix=std::make_unique<Design>(*des);
    int min_broken=1000,zero_broken=0;
    for(const auto& e:window_elite_snapshots) {
        Comparator candidate=comp;candidate.edge=e.edges;candidate.polarity=e.polarity;candidate.rebuild();
        int broken=0;for(const auto& u:des->unit)if(u.b>=0)broken+=!candidate.compatible(des->A[u.a],des->A[u.b]);
        min_broken=std::min(min_broken,broken);zero_broken+=broken==0;
    }
    std::cerr<<"elite_min_broken = "<<min_broken<<"\\nelite_zero_broken = "<<zero_broken<<'\\n';
    std::unique_ptr<Design> best_assignment;'''
assert needle in s;s=s.replace(needle,insert,1)
p=R/'solutions/deval-elite-probe';p.mkdir();(p/'main.cpp').write_text(s)
(p/'README.md').write_text('改良元: `solutions/deval-ordered8`。\n\n診断用。窓割当てのelite poolから、同じ汎用窓集合を持つ別配置を保存する。焼きなましの共有前半のペアについて、各別配置で整合性を失うペア数を記録する。探索・選択は変えず、出力は同じ。elite_total / same_set / alternates、elite_min_broken / zero_brokenを出す。\n')
print(p.name,len(s.encode()))
