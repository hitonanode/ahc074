from pathlib import Path
R=Path(__file__).resolve().parents[2]
B=(R/'solutions/dcomp-t11-seed-one/main.cpp').read_text()
for method in ['tie','length']:
 s=B
 a='''                    std::stable_sort(neutral_seeds.begin(),neutral_seeds.end(),by_cost);
                    for(const auto& second:neutral_seeds) {'''
 assert s.count(a)==1
 rank='''                        restore(c.state);const auto f=tie_features(c.path.size());
                        double priority=c.cost;
                        for(int j=0;j<9;++j)priority+=kTieCoef[j]*f[j];
'''if method=='tie'else'''                        const double priority=-double(c.path.size());
'''
 s=s.replace(a,'''                    struct RankedSeed{double priority,cost;size_t index;};
                    std::vector<RankedSeed> ranked;
                    for(size_t i=0;i<neutral_seeds.size();++i) {
                        const auto& c=neutral_seeds[i];
                        if(c.state.order==parent_order || c.cost>parent_value+0.3)continue;
'''+rank+'''                        ranked.push_back({priority,c.cost,i});
                    }
                    restore(incumbent);
                    std::stable_sort(ranked.begin(),ranked.end(),[](const auto& a,const auto& b) {
                        return a.priority!=b.priority?a.priority<b.priority:a.cost<b.cost;
                    });
                    for(const auto& rank:ranked) {
                        const auto& second=neutral_seeds[rank.index];''')
 d=R/'solutions'/('dcomp-t11-seedrank-'+method);assert not d.exists();d.mkdir();(d/'main.cpp').write_text(s)
 desc='既存near-tie補正を加えた費用の小さい順'if method=='tie'else'操作数が多い順、同数なら元の費用が小さい順'
 (d/'README.md').write_text('改良元: solutions/dcomp-t11-seed-one\n\n第二親を'+desc+'で選ぶ。元の親と異なる完成stack、元の費用gap .3以内、追加親は一つ、1→1だけという条件は同じ。補正係数の学習・変更はしない。修復前の最小費用以外の選び方が同じ予算で役立つか測る。\n\n両コンパイラ共通予算、時計分岐なし。ログ・trace・profiler・実験スイッチ・目次と段・DesignStoreを保持する。\n')
