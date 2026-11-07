from pathlib import Path
P=Path(__file__).resolve().parent;R=P.parents[1]
b=(R/'solutions/deval-ordered8/main.cpp').read_text()
for name,scale in [('deval-mdp-rate50','.5'),('deval-mdp-rate75','.75'),('deval-mdp-depth','.4+.6*double(c+1)*(c+1)/(H*H)')]:
 s=b.replace('''            if (!colmdp[c].build(count, rate, adaptive_holes[c], config.iters''',f'''            auto lambda=adaptive_holes[c];
            for(double& x:lambda)x*=({scale});
            if (!colmdp[c].build(count, rate, lambda, config.iters''',1)
 p=R/'solutions'/name;p.mkdir();(p/'main.cpp').write_text(s)
 (p/'README.md').write_text(f'改良元: `solutions/deval-ordered8`。\n\n列MDPが受け取るハンドルの色需要だけを `{scale}` 倍にする。穴の要求がfillerで処理される分を近似して引く。1注文先の費用、filler需要による紙の重み、実際の色合わせは変えない。設計・探索回数は同じ。時計による切り替えなし。\n')
 print(name,len(s.encode()))
name='deval-mdp-cluster'
code='''            // Two weight classes per color, fitted to the actual filler-aware
            // paper rates rather than only the number of dedicated targets.
            count.fill(0);weight.fill(0.);
            for(int color=0;color<2;++color) {
                std::vector<int> group;
                for(int k=0;k<K;++k)if(col_of[k]==c && (column_color[k]&1)==color)group.push_back(k);
                std::stable_sort(group.begin(),group.end(),[&](int a,int b){return adaptive_weights[a]<adaptive_weights[b];});
                const int n=group.size();int split=n;double best=1e100;
                for(int cut=1;cut<=n;++cut) {
                    double error=0;
                    for(auto [lo,hi]:{std::pair{0,cut},std::pair{cut,n}})if(hi>lo) {
                        double mean=0;for(int i=lo;i<hi;++i)mean+=adaptive_weights[group[i]];mean/=hi-lo;
                        for(int i=lo;i<hi;++i){double d=adaptive_weights[group[i]]-mean;error+=d*d;}
                    }
                    if(error<best-1e-12)best=error,split=cut;
                }
                for(int i=0;i<n;++i){int k=group[i],t=color+2*(i>=split);colmdp_type[k]=t;++count[t];weight[t]+=adaptive_weights[k];}
            }
'''
s=b.replace('            for (int t = 0; t < 4; t++) rate[t] = count[t] ? weight[t] / count[t] / P : 0.0;',code+'            for (int t = 0; t < 4; t++) rate[t] = count[t] ? weight[t] / count[t] / P : 0.0;',1)
p=R/'solutions'/name;p.mkdir();(p/'main.cpp').write_text(s)
(p/'README.md').write_text('改良元: `solutions/deval-ordered8`。\n\n列MDPの紙の4種類を、担当目標数×色から、filler需要を含む紙の重みの2群×色へ替える。同色ごとに重み順の全分割を比較し、群内二乗誤差が最小の2群にする。群ごとの平均需要で従来と同じMDPを解く。1注文先の費用は紙ごとの値を保つ。設計・探索回数は同じ、時計による切り替えなし。\n')
print(name,len(s.encode()))
