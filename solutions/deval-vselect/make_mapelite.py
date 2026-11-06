"""Reuse alternative window assignments already visited by the mapper."""
from pathlib import Path
from make_col import refresh_contents
HERE=Path(__file__).resolve().parent
DEST=HERE.parent/'deval-vmap'
src=(HERE.parent/'deval-vclean/main.cpp').read_text()
needle='WindowStats assign_windows('
lo=src.index(needle)
src=src[:lo]+'''// ==== Window assignment: export existing elites for design selection ====
struct DevalMap {
    std::vector<u64> A;
    std::vector<int> permutation,polarity;
    std::vector<std::pair<int,int>> edge;
    double cost;
};
std::vector<DevalMap> deval_maps;
'''+src[lo:]
needle='    stats.gobj_after = cur;\n    for (int j = 0; j < g; j++) {'
assert needle in src
src=src.replace(needle,'''    stats.gobj_after = cur;
    deval_maps.clear();
    auto save_map=[&](const std::vector<int>& ord,const std::vector<u64>& masks,u64 colors,double cost) {
        DevalMap saved;
        saved.A=A;saved.permutation=permutation;saved.edge=edges;saved.polarity=polarity;saved.cost=cost;
        for(int j=0;j<g;++j) {
            int e=0;while(e<ne&&!(masks[e]>>ord[j]&1))++e;
            assert(e<ne);saved.edge[j]=ep[e];saved.polarity[j]=colors>>ord[j]&1;
        }
        for(int j=0;j<64;++j)saved.permutation[j]=permutation[ord[j]];
        for(auto& a:saved.A) {
            u64 b=0;for(int j=0;j<64;++j)b|=((a>>ord[j])&1)<<j;a=b;
        }
        deval_maps.push_back(std::move(saved));
    };
    save_map(order,mask,pol,cur);
    std::vector<std::pair<double,int>> ranked_maps;
    for(int i=0;i<int(elites.size());++i)if(elites[i].ready)ranked_maps.emplace_back(elites[i].cost,i);
    std::sort(ranked_maps.begin(),ranked_maps.end());
    for(auto [cost,i]:ranked_maps) {
        const auto& saved=elites[i];
        std::vector<u64> masks(ne);
        for(u64 z=saved.generic;z;z&=z-1) {int j=__builtin_ctzll(z);masks[saved.which[j]]|=u64(1)<<j;}
        if(masks==mask&&!((saved.pol^pol)&saved.generic))continue;
        std::vector<int> ord;
        for(int j:order)if(saved.generic>>j&1)ord.push_back(j);
        for(int j:order)if(!(saved.generic>>j&1))ord.push_back(j);
        save_map(ord,masks,saved.pol,cost);
    }
    std::cerr << "dv_map_pool = " << deval_maps.size() << '\\n';
    for (int j = 0; j < g; j++) {''')
src=src.replace('env_real("DEVAL_MODE",1)','env_real("DEVAL_MODE",0)')
src=src.replace('env_int("DEVAL_CANDIDATES"):4','env_int("DEVAL_CANDIDATES"):2')
needle='        } else if(i) {\n            des=std::make_unique<Design>(A,M,G);'
assert needle in src
src=src.replace(needle,'''        } else if(i) {
            if(!deval_maps.empty()&&int(deval_maps.front().edge.size())==G) {
                const auto& selected_map=deval_maps[i%deval_maps.size()];
                A=selected_map.A;permutation=selected_map.permutation;
                comp.edge=selected_map.edge;comp.polarity=selected_map.polarity;comp.rebuild();
                std::cerr << "dv_map_gap = " << selected_map.cost-deval_maps.front().cost << '\\n';
            }
            des=std::make_unique<Design>(A,M,G);''')
src=refresh_contents(src)
assert len(src.encode())<=520000,len(src.encode())
DEST.mkdir(exist_ok=True)
(DEST/'main.cpp').write_text(src)
(DEST/'README.md').write_text('''# deval-vmap

改良元: `solutions/deval-vclean`。

窓割当てが元から保持していた 8 個の良い状態を、設計候補として再利用する。追加の窓探索は行わない。最良割当てと、費用順の別の割当てから初期化して焼きなましを行い、完成後の V16 で選ぶ。候補内の総反復数は `ANNEAL_ITERS`、候補数は `DEVAL_CANDIDATES`（既定 2）。仕上げは親と同じ 50,000 回と再割当て 2 回。

`dv_map_pool` は取り出せた割当て数、`dv_map_gap` は元の最良割当てからの gobj の差。時間ガード、DesignStore、既存診断は維持。生成は `solutions/deval-vselect/make_mapelite.py`。
''')
print('source bytes',len(src.encode()))
