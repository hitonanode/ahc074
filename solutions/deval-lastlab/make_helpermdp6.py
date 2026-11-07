from pathlib import Path
P=Path(__file__).resolve().parent;root=P.parents[1]
s=(root/'solutions/deval-helpeq1/main.cpp').read_text()
s=s.replace('double score = pk.distance + dep + 1.8;','double score = pk.distance + dep + 1.8 + .5*future[pk.goal];')
s=s.replace('pair_picks.push_back({pp.estimate + pk.distance, pk});','pair_picks.push_back({pp.estimate + pk.distance + .5*future[pk.goal], pk});')
def emit(name,x,description):
    p=root/'solutions'/name;p.mkdir();(p/'main.cpp').write_text(x)
    (p/'README.md').write_text('改良元: `solutions/deval-helpeq1`。\n\n'+description+'\n\n同generic距離の追加helperは上位1件、通常候補と合計6件のまま。実行した候補は従来通り実際のplan_costと合法性で評価する。設計と探索予算は固定し、時計による切替えはない。\n')
    assert len(x.encode())<=522000;print(name,len(x.encode()))
emit('deval-helpeq-rank',s,'helper候補の事前順位にも既存のgeneric末端価値future×0.5を加える。')
old='''        std::array<int, K> helper_depth{};'''
new='''        // Native column-MDP estimate of extracting a helper after its prefix
        // has been dug. F(suffix) already allows optimal reinsertion of that prefix.
        std::array<double,K> helper_mdp{};
        if(colmdp_next) {
            std::array<int,64> counts{},ranks{};
            for(int i=K-1;i>=0;--i) {
                const int k=order[i],c=col_of[k];if(c<0 || !colmdp[c].ok)continue;
                const auto& m=colmdp[c];
                helper_mdp[k]=m.F[m.offset[counts[c]]+ranks[c]];
                counts[c]+=m.radix[colmdp_type[k]];
                ranks[c]+=m.before[counts[c]][colmdp_type[k]];
            }
            for(int k=0;k<K;++k) {
                const int c=col_of[k];if(c<0 || !colmdp[c].ok)continue;
                const auto& m=colmdp[c];
                helper_mdp[k]=colmdp_next_weight[c]*(helper_mdp[k]-m.F[m.offset[counts[c]]+ranks[c]]);
            }
        }
        std::array<int, K> helper_depth{};'''
assert s.count(old)==1
t=s.replace(old,new).replace('double score = pk.distance + dep + 1.8 + .5*future[pk.goal];','double score = pk.distance + dep + 1.8 + .5*future[pk.goal] + helper_mdp[h.paper];')
t=t.replace('double estimate = depths[x] + depths[y] + 3.6;','double estimate = depths[x] + depths[y] + 3.6 + helper_mdp[x] + helper_mdp[y];')
emit('deval-helpeq-mdp',t,'helperの事前順位に、generic future×0.5と既存列MDPの差を加える。列MDPの差は、掘り出した紙までのprefixを除いたsuffixのF値−現在列のF値に、既存の終端MDP係数を掛けたもの。Fは取り出したprefixの最良再挿入を表す。状態を変更せず、全列のsuffix rankを逆順1走査で計算する。2枚helperは別列なので、それぞれの差を加算する。')
