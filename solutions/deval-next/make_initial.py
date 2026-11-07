from pathlib import Path
r=Path(__file__).resolve().parents[2];b=(r/'solutions/deval-seven-wide/main.cpp').read_text()
helper='''// ==== Initial column order ====

// Start each column in a low-cost state before any orders are observed.
// This changes only the order/numbering of papers within the same column.
void improve_initial_columns(DesignState& state) {
    const double begin=elapsed_sec();
    Solver probe=make_solver(state);
    probe.adaptive_weights.assign(K,0.);probe.adaptive_holes.assign(probe.H,{0.,0.});
    std::array<int,K> frequency{};
    for(int u=0;u<P;++u) {
        const int k=probe.ded[u];++frequency[k];probe.adaptive_weights[k]+=1.;
        for(int c=0;c<probe.H;++c)if(!(probe.h_opq[k]>>c&1))probe.adaptive_holes[c][probe.h_blk[k]>>c&1]+=0.;
        for(int c=0;c<probe.H;++c)if(!(probe.h_opq[k]>>c&1))probe.adaptive_holes[c][probe.A[u]>>probe.handle[c]&1]+=1./P;
    }
    probe.add_filler_demand();
    INITIAL_BUILD
    std::array<int,K> destination;std::iota(destination.begin(),destination.end(),0);
    const auto original=state.papers;
    double gain=0;int changed=0;
    for(int c=0;c<probe.H;++c) {
        std::vector<int> slots;
        for(int k=0;k<K;++k)if(state.columns[k]==c)slots.push_back(k);
        std::vector<int> sequence;
        INITIAL_SELECT
        for(int j=0;j<int(slots.size());++j) {
            const int old=sequence[j],to=slots[j];
            state.papers[to]=original[old];destination[old]=to;changed+=old!=to;
        }
    }
    for(int u=0;u<P;++u)state.ded[u]=destination[state.ded[u]];
    std::cerr<<"initial_order_changed = "<<changed<<"\\ninitial_order_model_gain = "<<gain
             <<"\\ninitial_order_sec = "<<elapsed_sec()-begin<<'\\n';
}

'''
# Remove a harmless placeholder, to leave only the exact demand accumulation.
helper=helper.replace('        for(int c=0;c<probe.H;++c)if(!(probe.h_opq[k]>>c&1))probe.adaptive_holes[c][probe.h_blk[k]>>c&1]+=0.;\n','')
mdp='''        const auto& m=probe.colmdp[c];
        if(!m.ok){sequence=slots;}
        else {
            std::array<std::vector<int>,4> groups;
            for(int k:slots)groups[probe.colmdp_type[k]].push_back(k);
            for(auto& group:groups)std::stable_sort(group.begin(),group.end(),[&](int a,int b){return probe.adaptive_weights[a]>probe.adaptive_weights[b];});
            int code=0,oldrank=0;
            for(int j=int(slots.size())-1;j>=0;--j){int t=probe.colmdp_type[slots[j]];code+=m.radix[t];oldrank+=m.before[code][t];}
            const int first=m.offset[m.top];
            const int best=int(std::min_element(m.F.begin()+first,m.F.begin()+first+m.full)-m.F.begin());
            gain+=m.F[first+oldrank]-m.F[best];
            int rank=best-first,remaining=m.top;
            std::array<int,4> used{};
            for(int j=0;j<int(slots.size());++j) {
                for(int t=0;t<4;++t)if(used[t]<int(groups[t].size())) {
                    const int rest=remaining-m.radix[t];
                    const int ways=(rest+1<int(m.offset.size())?m.offset[rest+1]:int(m.F.size()))-m.offset[rest];
                    if(rank>=ways){rank-=ways;continue;}
                    sequence.push_back(groups[t][used[t]++]);remaining=rest;break;
                }
            }
        }
'''
rank='''        std::array<std::vector<int>,2> groups;
        for(int k:slots)groups[(probe.paper[k].black>>probe.handle[c])&1].push_back(k);
        for(auto& group:groups)std::stable_sort(group.begin(),group.end(),[&](int a,int b){return probe.adaptive_weights[a]>probe.adaptive_weights[b];});
        const int n0=groups[0].size(),n1=groups[1].size(),stride=n1+1;
        std::vector<double> dp((n0+1)*stride,1e100);std::vector<int> prev(dp.size());dp[0]=0;
        for(int i=0;i<=n0;++i)for(int j=0;j<=n1;++j)for(int color=0;color<2;++color) {
            int used=color?j:i;if(used>=int(groups[color].size()))continue;
            const int k=groups[color][used],to=(i+(color==0))*stride+j+(color==1);
            const double value=dp[i*stride+j]+probe.adaptive_weights[k]*(i+j)/P+(used==0?probe.adaptive_holes[c][color]*(i+j):0.);
            if(value<dp[to])dp[to]=value,prev[to]=color;
        }
        int i=n0,j=n1;
        while(i+j){int color=prev[i*stride+j];sequence.push_back(groups[color][color?--j:--i]);}
        std::reverse(sequence.begin(),sequence.end());
        std::array<bool,2> seen{};double old=0;
        for(int j=0;j<int(slots.size());++j){int k=slots[j],color=(probe.paper[k].black>>probe.handle[c])&1;old+=probe.adaptive_weights[k]*j/P;if(!seen[color])old+=probe.adaptive_holes[c][color]*j;seen[color]=true;}
        gain+=old-dp.back();
'''
for name,build,select in [('deval-initial-mdp','probe.init_colmdp();',mdp),('deval-initial-rank','',rank)]:
 s=b
 s=s.replace('//   V: design-only expected moves','//   Initial column order\n//   V: design-only expected moves',1)
 marker='// ==== V: design-only expected moves ===='
 s=s.replace(marker,helper.replace('INITIAL_BUILD',build).replace('INITIAL_SELECT',select)+marker,1)
 needle='''    if(!finished)state.emergency=true;
    std::cerr << chosen_log;'''
 assert needle in s;s=s.replace(needle,'''    if(!finished)state.emergency=true;
    if(finished)improve_initial_columns(state);
    std::cerr << chosen_log;''',1)
 p=r/'solutions'/name;p.mkdir(exist_ok=True);(p/'main.cpp').write_text(s);assert len(s.encode())<=520000
 (p/'README.md').write_text(f'''改良元: `solutions/deval-seven-wide`\n\n完成設計をVで選んだ後、注文を知らずに列内の初期の紙の順番を最適化する。{('既存の列MDPを作り、各列の完全状態で相対価値Fが最小の型列を選ぶ。同じ型の紙はfiller需要を含む重み順に置く。' if build else '同じ色の紙をfiller需要を含む重み順にし、2色の列の混ぜ方を小さいDPで選ぶ。次の1注文の取り出しとハンドル修復の模型費用を最小にする。')}\n\n紙の模様と所属列は保ち、列内の紙番号とdedを対応して更新する。DesignStoreには更新後の設計を保存し、リプレイはそのまま読み込む。最適化は各候補ではなく最終設計に一度だけ。`initial_order_changed` は変わった位置数、`initial_order_model_gain` は模型の差、`initial_order_sec` は追加時間。全探索予算は固定で時間不足による変更はない。\n''');print(name,len(s.encode()))
