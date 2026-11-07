from pathlib import Path
P=Path(__file__).resolve().parent;R=P.parents[1]
b=(R/'solutions/deval-ordered8/main.cpp').read_text()
mdp='''
        // Fixed-horizon value iteration on the 720 generic-sheet orders.
        // Empty requests leave this layer unchanged and cancel in relative value.
        if(cnt) {
            const double start=elapsed_sec();
            for(int iteration=0;iteration<12;++iteration) {
                std::vector<double> next(n,0.);
                for(int u=0;u<P;++u)if(!sat[u].empty()) {
                    for(int s=0;s<n;++s) {
                        double v=1e30;
                        for(int t:sat[u])v=std::min(v,comparator.distance(s,t)+.9*future[t]);
                        next[s]+=v/cnt;
                    }
                }
                const double mean=std::accumulate(next.begin(),next.end(),0.)/n;
                for(double& v:next)v-=mean;
                future=std::move(next);
            }
            std::cerr<<"generic_value_sec = "<<elapsed_sec()-start<<"\\ngeneric_value_span = "
                     <<*std::max_element(future.begin(),future.end())-*std::min_element(future.begin(),future.end())<<'\\n';
        }
'''
for name,use_mdp,weight in [('deval-genlook',True,0),('deval-genone50',False,.5),('deval-genbias25',True,.25),('deval-genbias50',True,.5),('deval-genbias100',True,1.)]:
 s=b
 end='''        if (cnt)
            for (auto& f : future) f /= cnt;
    }
'''
 assert end in s
 if use_mdp:s=s.replace(end,end[:-6]+mdp+'    }\n',1)
 if weight:
  needle='''    // The cost of a plan of `moves` moves that leaves the current state (process).'''
  helper=f'''    // Lexicographic permutation rank without allocating a vector.
    double generic_bias() const {{
        if(future.empty())return 0.;
        unsigned used=0;int rank=0,count=0;
        for(int k:order)if(k<M) {{
            rank=rank*(M-count)+__builtin_popcount(((1U<<k)-1)&~used);
            used|=1U<<k;if(++count==M)break;
        }}
        return {weight}*future[rank];
    }}
'''
  s=s.replace(needle,helper+needle,1)
  s=s.replace('return moves + filler_charge(split) + kEndWeight * adaptive_next_cost(split);','return moves + filler_charge(split) + (kEndWeight * adaptive_next_cost(split) + generic_bias());',1)
  s=s.replace('memo->next_cost = kEndWeight * adaptive_next_cost(split);','memo->next_cost = kEndWeight * adaptive_next_cost(split) + generic_bias();',1)
  s=s.replace('baseline_next = kEndWeight * adaptive_next_cost(baseline_split);','baseline_next = kEndWeight * adaptive_next_cost(baseline_split) + generic_bias();',1)
 p=R/'solutions'/name;p.mkdir();(p/'main.cpp').write_text(s)
 (p/'README.md').write_text(f'改良元: `solutions/deval-ordered8`。\n\n設計と探索幅は同じ。汎用紙6枚の順序の将来価値を'+('割引率0.9、12回の相対価値反復で計算する。各バーコードで合法な汎用紙の順序への最小移動数と次状態価値を平均する。' if use_mdp else '既存の1注文先の最小移動数の平均とする。')+f'現在の汎用紙計画の同手数の選択に使う。計画全体の末端費用には、この価値×{weight}を加える。計画を再検査するmemoにも同じ項を加える。注文列は未知のまま、固定予算で動く。\n')
 print(name,len(s.encode()))
