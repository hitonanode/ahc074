            // Fit at most four weight classes, allowing 3+1 as well as 2+2
            // across colors. Bound both full and partial MDP state counts.
            std::array<std::vector<int>,2> group;
            for(int k=0;k<K;++k)if(col_of[k]==c)group[column_color[k]&1].push_back(k);
            for(auto& g:group)std::stable_sort(g.begin(),g.end(),[&](int a,int b){return adaptive_weights[a]<adaptive_weights[b];});
            struct Part { int n;std::array<int,3> end{};double error=0; };
            std::array<std::vector<Part>,2> parts;
            for(int b=0;b<2;++b) {
                const int n=group[b].size();
                std::vector<double> sum(n+1),sq(n+1);
                for(int j=0;j<n;++j){const double w=adaptive_weights[group[b][j]];sum[j+1]=sum[j]+w;sq[j+1]=sq[j]+w*w;}
                auto error=[&](int a,int z){return std::max(0.,sq[z]-sq[a]-(sum[z]-sum[a])*(sum[z]-sum[a])/(z-a));};
                parts[b].push_back({1,{n,0,0},error(0,n)});
                for(int i=1;i<n;++i) {
                    parts[b].push_back({2,{i,n,0},error(0,i)+error(i,n)});
                    for(int j=i+1;j<n;++j)parts[b].push_back({3,{i,j,n},error(0,i)+error(i,j)+error(j,n)});
                }
            }
            std::array<long long,ColumnMdp::kMaxLength+1> fact{};fact[0]=1;
            for(int j=1;j<=ColumnMdp::kMaxLength;++j)fact[j]=fact[j-1]*j;
            auto states=[&](const std::array<int,4>& q,bool all) {
                long long result=0;
                if(!all)return fact[q[0]+q[1]+q[2]+q[3]]/(fact[q[0]]*fact[q[1]]*fact[q[2]]*fact[q[3]]);
                for(int a=0;a<=q[0];++a)for(int b=0;b<=q[1];++b)
                for(int d=0;d<=q[2];++d)for(int e=0;e<=q[3];++e)
                    result+=fact[a+b+d+e]/(fact[a]*fact[b]*fact[d]*fact[e]);
                return result;
            };
            const int length=group[0].size()+group[1].size();
            std::array<int,4> type_colors{0,1,0,1};
            if(length<=ColumnMdp::kMaxLength) {
                const auto maxfull=std::min(config.max_full,QUANT_BUDGET*states(count,false));
                const auto maxsub=std::min(config.max_sequences,QUANT_BUDGET*states(count,true));
                double best=1e100;int first=-1,second=-1;
                for(int i=0;i<int(parts[0].size());++i)for(int j=0;j<int(parts[1].size());++j) {
                    const auto& a=parts[0][i];const auto& b=parts[1][j];
                    if(a.n+b.n>4 || a.error+b.error>=best-1e-12)continue;
                    std::array<int,4> q{};int t=0;
                    for(const auto* p:{&a,&b})for(int z=0,lo=0;z<p->n;lo=p->end[z],++z)q[t++]=p->end[z]-lo;
                    if(states(q,false)>maxfull || states(q,true)>maxsub)continue;
                    best=a.error+b.error;first=i;second=j;
                }
                if(first>=0) {
                    count.fill(0);weight.fill(0.);int t=0;
                    for(int b=0;b<2;++b) {
                        const auto& p=parts[b][b?second:first];
                        for(int z=0,lo=0;z<p.n;lo=p.end[z],++z,++t) {
                            type_colors[t]=b;
                            for(int i=lo;i<p.end[z];++i){const int k=group[b][i];colmdp_type[k]=t;++count[t];weight[t]+=adaptive_weights[k];}
                        }
                    }
                }
            }
